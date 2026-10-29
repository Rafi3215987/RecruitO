from datetime import datetime, timedelta, timezone
import base64
import binascii
import hashlib
import logging
import os
import secrets
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import delete, select, update

from app.db.session import SessionLocal
from app.dependencies import require_roles
from app.models.application import Application
from app.models.interview import Interview
from app.models.user import User
from app.models.job import Job
from app.models.audit_log import AuditLog
from app.models.notification import Notification
from app.models.screening_score import InterviewConsent, InterviewEvaluation, TranscriptSegment, ScreeningScore, BiometricEnrollment
from app.models.user import CandidateProfile
from app.schemas.interview import (
    InterviewResponse,
    InterviewScheduleRequest,
    InterviewerApplicationItem,
    InterviewerInterviewItem,
    ManagerInterviewChange,
    MockTranscriptImportRequest,
)
from app.services.notifications import queue_email, queue_status_email
from app.services.transcription import transcribe_audio_chunk
from app.services.face_biometrics import compare_embedding, MAX_IMAGE_BYTES
from app.services.screening import extract_resume_text
from app.models.job_requirement import JobRequirement
from app.models.password_reset import PasswordResetToken
from app.graphs.interview_analysis_graph import interview_analysis_graph


router = APIRouter(prefix="/applications", tags=["interviews"])
interview_access_router = APIRouter(prefix="/interviews", tags=["interview room"])
me_router = APIRouter(prefix="/me", tags=["interviewer dashboard"])
god_mode_interviews_router = APIRouter(prefix="/admin/interviews", tags=["hiring manager god mode"])
_room_sockets: dict[int, dict[str, WebSocket]] = {}
_transcript_sockets: dict[int, dict[str, WebSocket]] = {}
_candidate_upload_dir = Path(os.getenv("CANDIDATE_UPLOAD_DIR", "/data/candidate-resumes"))


def _cancel_pending_interviewer_reminders(session, application_id: int, interview_id: int) -> None:
    session.execute(
        update(Notification)
        .where(
            Notification.application_id == application_id,
            Notification.status_key.like(f"interviewer-reminder:{interview_id}:%"),
            Notification.state.in_(("pending", "failed", "sending")),
        )
        .values(state="cancelled", recipient_email="", body="", payload=None, available_at=None)
    )


def _join_window_open(interview: Interview, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    start = interview.scheduled_at.astimezone(timezone.utc)
    return start - timedelta(minutes=15) <= now <= start + timedelta(minutes=interview.duration_minutes + 30)


def _calendar_payload(interview: Interview, job_title: str, join_url: str) -> dict:
    start = interview.scheduled_at.astimezone(timezone.utc)
    end = start + timedelta(minutes=interview.duration_minutes)
    start_stamp = start.strftime("%Y%m%dT%H%M%SZ")
    end_stamp = end.strftime("%Y%m%dT%H%M%SZ")
    ics = "\r\n".join([
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//RecruitO//Interview//EN",
        "METHOD:REQUEST", "BEGIN:VEVENT", f"UID:recruito-interview-{interview.id}@recruito.local",
        f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART:{start_stamp}", f"DTEND:{end_stamp}",
        f"SUMMARY:RecruitO interview - {job_title}",
        f"DESCRIPTION:Join your interview: {join_url}", "END:VEVENT", "END:VCALENDAR", "",
    ])
    params = {
        "action": "TEMPLATE", "text": f"RecruitO interview - {job_title}",
        "dates": f"{start_stamp}/{end_stamp}", "details": f"Interview room: {join_url}",
    }
    return {
        "ics": ics,
        "calendar_url": "https://calendar.google.com/calendar/render?" + urlencode(params),
    }


@router.put(
    "/{application_id}/interview",
    response_model=InterviewResponse,
)
def schedule_interview(
    application_id: int,
    request: InterviewScheduleRequest,
    _current_user: User = Depends(require_roles("hiring_manager")),
):
    with SessionLocal() as session:
        interviewer = session.scalar(
            select(User).where(User.id == request.interviewer_id, User.role == "interviewer", User.is_active.is_(True))
        )
        if interviewer is None:
            raise HTTPException(status_code=422, detail="Choose an active interviewer")
        application = session.scalar(
            select(Application).where(Application.id == application_id)
        )
        if application is None:
            raise HTTPException(
                status_code=404,
                detail="Application not found",
            )
        if application.candidate_removed_at is not None or application.status == "withdrawn":
            raise HTTPException(status_code=409, detail="A withdrawn application cannot be scheduled for an interview")

        interview = session.scalar(
            select(Interview).where(
                Interview.application_id == application_id
            )
        )

        previous_interviewer_id = interview.interviewer_id if interview is not None else None
        if interview is None:
            interview = Interview(application_id=application_id)
            session.add(interview)
        else:
            _cancel_pending_interviewer_reminders(session, application.id, interview.id)

        interview.scheduled_at = request.scheduled_at.astimezone(timezone.utc)
        interview.duration_minutes = request.duration_minutes
        interview.interviewer_id = interviewer.id
        interview.status = "scheduled"
        interview.manager_removed_at = None
        interview.candidate_joined_at = None
        interview.started_at = None
        interview.ended_at = None
        raw_token = secrets.token_urlsafe(32)
        interview.token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        interview.token_expires_at = interview.scheduled_at + timedelta(minutes=interview.duration_minutes + 30)
        # Insert now (with required fields set) so interview.id is available for status keys.
        session.flush()
        application.status = "interview scheduled"
        application.scheduling_status = "scheduled"
        application.scheduling_processing_at = None
        application.scheduling_next_attempt_at = None
        application.scheduling_error_code = None

        job = session.get(Job, application.job_id)
        candidate = session.get(User, application.candidate_id)
        candidate_email = application.candidate_email or (candidate.email if candidate else "")
        public_base = os.getenv("PUBLIC_BASE_URL", "http://localhost:5500").rstrip("/")
        join_url = f"{public_base}/interview.html?token={raw_token}"
        calendar = _calendar_payload(interview, job.title if job else "Interview", join_url)
        queue_email(
            session,
            application_id=application.id,
            recipient=candidate_email,
            status_key=f"interview-invite:{interview.id}:{interview.scheduled_at.isoformat()}",
            subject=f"Interview scheduled: {job.title if job else 'RecruitO'}",
            body=(
                f"Your interview is scheduled for {interview.scheduled_at.isoformat()} "
                f"({interview.duration_minutes} minutes).\n\nJoin: {join_url}\n"
                f"Add to your calendar: {calendar['calendar_url']}\nAn .ics calendar attachment is included."
            ),
            payload={**calendar, "join_url": join_url},
        )
        # Candidates whose account the manager created by CV import have no password
        # yet. Send the set-password invite now (at scheduling) so they can sign in
        # and join — only for those actually being interviewed.
        if candidate is not None and candidate.password_pending and candidate_email:
            invite_raw = secrets.token_urlsafe(32)
            session.add(PasswordResetToken(
                token_hash=hashlib.sha256(invite_raw.encode()).hexdigest(),
                user_id=candidate.id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            ))
            invite_link = f"{public_base}/reset-password.html?token={invite_raw}"
            queue_email(
                session,
                application_id=application.id,
                recipient=candidate_email,
                status_key=f"candidate-set-password:{candidate.id}:{interview.id}"[:80],
                subject=f"Set your password to join your {job.title if job else 'RecruitO'} interview",
                body=(
                    f"Your interview for {job.title if job else 'RecruitO'} has been scheduled.\n\n"
                    "Your profile was added by the hiring team, so set a password to activate your "
                    f"account and sign in (this link expires in 7 days):\n{invite_link}\n\n"
                    "After setting your password you'll be signed in automatically, and you can then "
                    "join the interview from the link in this email or from your dashboard."
                ),
            )
        queue_email(
            session,
            application_id=application.id,
            recipient=interviewer.email,
            status_key=f"interviewer-invite:{interviewer.id}:{interview.scheduled_at.isoformat()}",
            subject=f"Interview assigned: {job.title if job else 'RecruitO'}",
            body=(
                f"An interview is assigned to you for {interview.scheduled_at.isoformat()} "
                f"({interview.duration_minutes} minutes). Sign in to your RecruitO interviewer dashboard to join: "
                f"{public_base}/interviewer-dashboard.html"
            ),
            payload={"ics": calendar["ics"]},
        )
        reminder_available_at = max(
            interview.scheduled_at - timedelta(minutes=10),
            datetime.now(timezone.utc),
        )
        queue_email(
            session,
            application_id=application.id,
            recipient=interviewer.email,
            status_key=f"interviewer-reminder:{interview.id}:{interview.scheduled_at.isoformat()}:{interviewer.id}"[:80],
            subject=f"Interview reminder: {job.title if job else 'RecruitO'}",
            body=(
                f"Reminder for your interview for {job.title if job else 'RecruitO'}, scheduled at "
                f"{interview.scheduled_at.isoformat()}. Sign in to your RecruitO interviewer dashboard to join: "
                f"{public_base}/interviewer-dashboard.html"
            ),
            available_at=reminder_available_at,
        )
        if previous_interviewer_id and previous_interviewer_id != interviewer.id:
            previous_interviewer = session.get(User, previous_interviewer_id)
            if previous_interviewer:
                queue_email(
                    session,
                    application_id=application.id,
                    recipient=previous_interviewer.email,
                    status_key=f"interviewer-unassigned:{interview.id}:{interview.scheduled_at.isoformat()}"[:80],
                    subject="Interview assignment removed",
                    body=f"You are no longer assigned to the interview for {job.title if job else 'RecruitO'}.",
                )

        session.commit()
        session.refresh(interview)
        session.expunge(interview)
        return interview


@router.delete("/interviews/{interview_id}", status_code=204)
def remove_past_interview_from_manager_view(
    interview_id: int,
    actor: User = Depends(require_roles("hiring_manager")),
):
    with SessionLocal() as session:
        row = session.execute(
            select(Interview, Application, Job)
            .join(Application, Application.id == Interview.application_id)
            .join(Job, Job.id == Application.job_id)
            .where(Interview.id == interview_id)
        ).first()
        if row is None or row[0].manager_removed_at is not None:
            raise HTTPException(status_code=404, detail="Interview not found")

        interview, application, job = row
        now = datetime.now(timezone.utc)
        interview_end = interview.ended_at or (
            interview.scheduled_at + timedelta(minutes=interview.duration_minutes)
        )
        if interview_end > now:
            raise HTTPException(status_code=409, detail="Only past interviews can be removed")

        interview.manager_removed_at = now
        # Removing the interview also deletes the data it produced — the stored
        # transcript, the AI analysis, and the recorded consents — so nothing
        # about the conversation is kept once it is removed.
        transcript_deleted = session.execute(
            delete(TranscriptSegment).where(TranscriptSegment.interview_id == interview.id)
        ).rowcount
        analysis_deleted = session.execute(
            delete(InterviewEvaluation).where(InterviewEvaluation.interview_id == interview.id)
        ).rowcount
        consents_deleted = session.execute(
            delete(InterviewConsent).where(InterviewConsent.interview_id == interview.id)
        ).rowcount
        # The analysis is gone, so clear the interview's analysis bookkeeping too.
        interview.analysis_status = "not_started"
        interview.analysis_error_code = None
        session.add(AuditLog(
            actor_user_id=actor.id,
            action="manager_removed_past_interview_from_dashboard",
            target_type="interview",
            target_id=str(interview.id),
            before_values={
                "application_id": application.id,
                "job_title": job.title,
                "status": interview.status,
                "scheduled_at": interview.scheduled_at.isoformat(),
            },
            after_values={
                "hidden_from_manager_view": True,
                "transcript_segments_deleted": transcript_deleted,
                "analysis_records_deleted": analysis_deleted,
                "consents_deleted": consents_deleted,
            },
            reason="Hiring manager removed a past interview; transcript, analysis and consents deleted.",
        ))
        session.commit()


@god_mode_interviews_router.patch("/{interview_id}", response_model=InterviewResponse)
def change_interview(
    interview_id: int,
    request: ManagerInterviewChange,
    actor: User = Depends(require_roles("hiring_manager")),
):
    with SessionLocal() as session:
        row = session.execute(
            select(Interview, Application, Job, User)
            .join(Application, Application.id == Interview.application_id)
            .join(Job, Job.id == Application.job_id)
            .join(User, User.id == Application.candidate_id)
            .where(Interview.id == interview_id)
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Interview not found")
        interview, application, job, candidate = row
        previous_interviewer_id = interview.interviewer_id
        before = {"scheduled_at": interview.scheduled_at.isoformat(), "duration_minutes": interview.duration_minutes,
                  "interviewer_id": interview.interviewer_id, "status": interview.status}
        if request.cancel:
            if interview.status != "scheduled":
                raise HTTPException(status_code=409, detail="Only scheduled interviews can be cancelled")
            interview.status = "cancelled"
            interview.cancellation_reason = request.reason
            interview.token_hash = None
            interview.token_expires_at = None
            interview.interviewer_token_hash = None
            interview.interviewer_token_expires_at = None
            _cancel_pending_interviewer_reminders(session, application.id, interview.id)
            application.status = "selected for interview"
            application.scheduling_status = "manager_notified"
        else:
            if request.scheduled_at is None or request.duration_minutes is None or request.interviewer_id is None:
                raise HTTPException(status_code=422, detail="Rescheduling requires a time, duration, and interviewer")
            interviewer = session.scalar(select(User).where(
                User.id == request.interviewer_id, User.role == "interviewer", User.is_active.is_(True)))
            if interviewer is None:
                raise HTTPException(status_code=422, detail="Choose an active interviewer")
            _cancel_pending_interviewer_reminders(session, application.id, interview.id)
            interview.scheduled_at = request.scheduled_at.astimezone(timezone.utc)
            interview.duration_minutes = request.duration_minutes
            interview.interviewer_id = interviewer.id
            interview.status = "scheduled"
            interview.token_hash = None
            interview.interviewer_token_hash = None
            interview.interviewer_token_expires_at = None
            interview.token_expires_at = interview.scheduled_at + timedelta(minutes=interview.duration_minutes + 30)
            raw_token = secrets.token_urlsafe(32)
            interview.token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            application.scheduling_status = "scheduled"
            application.scheduling_error_code = None
        after = {"scheduled_at": interview.scheduled_at.isoformat(), "duration_minutes": interview.duration_minutes,
                 "interviewer_id": interview.interviewer_id, "status": interview.status}
        audit = AuditLog(actor_user_id=actor.id, action="cancel_interview" if request.cancel else "reschedule_or_reassign_interview",
            target_type="interview", target_id=str(interview.id), before_values=before,
            after_values=after, reason=request.reason)
        session.add(audit)
        session.flush()
        recipient = application.candidate_email or candidate.email
        public_base = os.getenv("PUBLIC_BASE_URL", "http://localhost:5500").rstrip("/")
        join_url = f"{public_base}/interview.html?token={raw_token}" if not request.cancel else ""
        calendar = _calendar_payload(interview, job.title, join_url) if not request.cancel else None
        assigned_for_event = session.get(User, interview.interviewer_id) if not request.cancel else None
        if not request.cancel and assigned_for_event is None:
            raise HTTPException(status_code=409, detail="The assigned interviewer is unavailable")
        queue_email(session, application_id=application.id, recipient=recipient,
            status_key=f"interview-change-candidate:{audit.id}",
            subject="Interview cancelled" if request.cancel else "Interview rescheduled",
            body=(f"Your interview was cancelled. Reason: {request.reason}" if request.cancel else
                  f"Your interview is rescheduled to {interview.scheduled_at.isoformat()} ({interview.duration_minutes} minutes).\n\nJoin: {join_url}\n"
                  f"Add to your calendar: {calendar['calendar_url']}\nAn .ics calendar attachment is included."),
            payload=None if request.cancel else calendar)
        if not request.cancel:
            assigned = session.get(User, interview.interviewer_id)
            if assigned:
                queue_email(session, application_id=application.id, recipient=assigned.email,
                    status_key=f"interview-change-interviewer:{audit.id}", subject="Interview assignment updated",
                    body=f"The interview for {job.title} is scheduled for {interview.scheduled_at.isoformat()}. Sign in to RecruitO to join.",
                    payload={"ics": calendar["ics"]})
            if previous_interviewer_id and previous_interviewer_id != interview.interviewer_id:
                previous = session.get(User, previous_interviewer_id)
                if previous:
                    queue_email(session, application_id=application.id, recipient=previous.email,
                        status_key=f"interview-unassigned:{audit.id}", subject="Interview assignment removed",
                        body=f"You are no longer assigned to the interview for {job.title}.")
            assigned = session.get(User, interview.interviewer_id)
            if assigned:
                reminder_available_at = max(
                    interview.scheduled_at - timedelta(minutes=10),
                    datetime.now(timezone.utc),
                )
                queue_email(
                    session,
                    application_id=application.id,
                    recipient=assigned.email,
                    status_key=f"interviewer-reminder:{interview.id}:{interview.scheduled_at.isoformat()}:{assigned.id}"[:80],
                    subject=f"Interview reminder: {job.title}",
                    body=(
                        f"Reminder for your interview for {job.title}, scheduled at "
                        f"{interview.scheduled_at.isoformat()}. Sign in to your RecruitO interviewer dashboard to join: "
                        f"{public_base}/interviewer-dashboard.html"
                    ),
                    available_at=reminder_available_at,
                )
        elif previous_interviewer_id:
            previous = session.get(User, previous_interviewer_id)
            if previous:
                queue_email(
                    session,
                    application_id=application.id,
                    recipient=previous.email,
                    status_key=f"interviewer-cancelled:{audit.id}",
                    subject="Interview cancelled",
                    body=f"The interview for {job.title} was cancelled. Reason: {request.reason}",
                )
        session.commit()
        session.refresh(interview)
        return interview


@god_mode_interviews_router.post("/{interview_id}/mock-transcript", status_code=201)
def import_mock_transcript(
    interview_id: int,
    request: MockTranscriptImportRequest,
    actor: User = Depends(require_roles("hiring_manager")),
):
    if os.getenv("APP_ENV", "production").lower() != "development":
        raise HTTPException(status_code=404, detail="Not found")
    with SessionLocal() as session:
        interview = session.get(Interview, interview_id)
        if interview is None:
            raise HTTPException(status_code=404, detail="Interview not found")
        rows = [TranscriptSegment(interview_id=interview_id, **segment.model_dump(), source="mock")
                for segment in request.segments]
        session.add_all(rows)
        session.add(AuditLog(
            actor_user_id=actor.id, action="import_mock_transcript", target_type="interview",
            target_id=str(interview_id), before_values=None,
            after_values={"segment_count": len(rows)}, reason=request.reason,
        ))
        session.commit()
        return {"interview_id": interview_id, "segments_imported": len(rows)}


@god_mode_interviews_router.post("/{interview_id}/analysis")
def analyze_interview(
    interview_id: int,
    current_user: User = Depends(require_roles("hiring_manager", "interviewer")),
):
    with SessionLocal() as session:
        row = session.execute(
            select(Interview, Application, Job)
            .join(Application, Application.id == Interview.application_id)
            .join(Job, Job.id == Application.job_id)
            .where(Interview.id == interview_id)
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Interview not found")
        interview, application, job = row
        if current_user.role == "interviewer" and interview.interviewer_id != current_user.id:
            raise HTTPException(status_code=404, detail="Interview not found")
        segments = session.scalars(select(TranscriptSegment).where(
            TranscriptSegment.interview_id == interview_id
        ).order_by(TranscriptSegment.started_at_seconds, TranscriptSegment.id)).all()
        requirements = session.scalars(select(JobRequirement).where(
            JobRequirement.job_id == job.id
        ).order_by(JobRequirement.id)).all()
        if not segments or not requirements:
            raise HTTPException(status_code=409, detail="A transcript and job requirements are needed before analysis")
        segment_data = [{"id": item.id, "speaker_role": item.speaker_role,
                         "started_at_seconds": item.started_at_seconds,
                         "ended_at_seconds": item.ended_at_seconds, "text": item.text} for item in segments]
        requirement_data = [{"text": item.text, "kind": item.kind,
                             "category": item.category, "weight": item.weight} for item in requirements]
        resume_path = (_candidate_upload_dir / application.resume_storage_key) if application.resume_storage_key else None
        resume_filename = application.resume_file_name or "resume.pdf"
        resume_text = None
        if resume_path and resume_path.is_file() and resume_path.parent.resolve() == _candidate_upload_dir.resolve():
            try:
                resume_text = extract_resume_text(resume_path.read_bytes(), resume_filename)
            except Exception:
                resume_text = None
    try:
        result = interview_analysis_graph.invoke({
            "interview_id": interview_id, "segments": segment_data,
            "requirements": requirement_data, "resume_text": resume_text,
        })
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("Interview analysis failed for interview %s", interview_id)
        raise HTTPException(status_code=502, detail="Interview analysis is temporarily unavailable") from exc
    return {"evaluation_id": result["evaluation_id"], **result["analysis"],
            "validation": result.get("validation"),
            "extended_assessment": result.get("extended_assessment"),
            "extended_assessment_status": result.get("extended_assessment_status", "resume_unavailable")}


@me_router.get("/interviews", response_model=list[InterviewerInterviewItem])
def list_assigned_interviews(current_user: User = Depends(require_roles("interviewer"))):
    with SessionLocal() as session:
        rows = session.execute(
            select(Interview, Application, Job, User)
            .join(Application, Application.id == Interview.application_id)
            .join(Job, Job.id == Application.job_id)
            .join(User, User.id == Application.candidate_id)
            .where(Interview.interviewer_id == current_user.id)
            .order_by(Interview.scheduled_at.asc())
        ).all()
        now = datetime.now(timezone.utc)
        active_rows = [
            row
            for row in rows
            if row[0].status not in {"completed", "cancelled", "no_show"}
            and (
                row[0].scheduled_at + timedelta(minutes=row[0].duration_minutes) > now
                or (row[0].started_at is not None and row[0].ended_at is None)
            )
        ]
        return [
            InterviewerInterviewItem(
                interview_id=interview.id,
                application_id=application.id,
                candidate_name=application.candidate_name or candidate.full_name,
                job_title=job.title,
                scheduled_at=interview.scheduled_at,
                duration_minutes=interview.duration_minutes,
                status=interview.status,
                join_url=(f"/interview.html?interview={interview.id}" if _join_window_open(interview, now) and interview.status == "scheduled" else None),
            )
            for interview, application, job, candidate in active_rows
        ]


@me_router.get("/interviewer-applications", response_model=list[InterviewerApplicationItem])
def list_job_applications_for_interviewer(current_user: User = Depends(require_roles("interviewer"))):
    with SessionLocal() as session:
        rows = session.execute(
            select(Application, Job, User)
            .join(Job, Job.id == Application.job_id)
            .join(User, User.id == Application.candidate_id)
            .order_by(Application.created_at.desc(), Application.id.desc())
        ).all()
        return [
            InterviewerApplicationItem(
                application_id=application.id,
                candidate_name=application.candidate_name or candidate.full_name,
                job_title=job.title,
                seniority=job.seniority,
                status=application.status,
                applied_at=application.created_at,
            )
            for application, job, candidate in rows
        ]


@interview_access_router.post("/{interview_id}/join-link")
def create_interview_join_link(
    interview_id: int,
    current_user: User = Depends(require_roles("candidate", "interviewer")),
):
    with SessionLocal() as session:
        row = session.execute(
            select(Interview, Application)
            .join(Application, Application.id == Interview.application_id)
            .where(Interview.id == interview_id)
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Interview not found")
        interview, application = row
        has_access = (
            current_user.role == "candidate" and application.candidate_id == current_user.id
        ) or (
            current_user.role == "interviewer" and interview.interviewer_id == current_user.id
        )
        if not has_access:
            raise HTTPException(status_code=404, detail="Interview not found")
        if interview.status != "scheduled" or not _join_window_open(interview):
            raise HTTPException(status_code=409, detail="The interview room is available only shortly before the scheduled time")
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires = interview.token_expires_at
        if current_user.role == "candidate":
            interview.token_hash = token_hash
            interview.token_expires_at = interview.scheduled_at + timedelta(minutes=interview.duration_minutes + 30)
            expires = interview.token_expires_at
        else:
            interview.interviewer_token_hash = token_hash
            interview.interviewer_token_expires_at = interview.scheduled_at + timedelta(minutes=interview.duration_minutes + 30)
            expires = interview.interviewer_token_expires_at
        session.commit()
        return {"token": raw_token, "expires_at": expires}


@interview_access_router.post("/validate-token")
def validate_interview_token(
    request: dict,
    current_user: User = Depends(require_roles("candidate", "interviewer")),
):
    token = request.get("token") if isinstance(request, dict) else None
    if not isinstance(token, str) or len(token) > 200:
        raise HTTPException(status_code=422, detail="Invalid interview link")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with SessionLocal() as session:
        row = session.execute(
            select(Interview, Application, Job, User)
            .join(Application, Application.id == Interview.application_id)
            .join(Job, Job.id == Application.job_id)
            .join(User, User.id == Application.candidate_id)
            .where((Interview.token_hash == token_hash) | (Interview.interviewer_token_hash == token_hash))
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Interview link is invalid or expired")
        interview, application, job, candidate = row
        now = datetime.now(timezone.utc)
        has_access = (
            current_user.role == "candidate" and application.candidate_id == current_user.id
        ) or (
            current_user.role == "interviewer" and interview.interviewer_id == current_user.id
        )
        if not has_access:
            raise HTTPException(status_code=404, detail="Interview link is invalid or expired")
        is_interviewer_token = interview.interviewer_token_hash == token_hash
        expires_at = interview.interviewer_token_expires_at if is_interviewer_token else interview.token_expires_at
        if (is_interviewer_token and current_user.role != "interviewer") or (not is_interviewer_token and current_user.role != "candidate"):
            raise HTTPException(status_code=404, detail="Interview link is invalid or expired")
        if interview.status != "scheduled" or not expires_at or now > expires_at or not _join_window_open(interview, now):
            raise HTTPException(status_code=409, detail="The interview room is outside its access window")
        return {
            "interview_id": interview.id,
            "candidate_name": application.candidate_name or candidate.full_name,
            "job_title": job.title,
            "scheduled_at": interview.scheduled_at,
            "duration_minutes": interview.duration_minutes,
            "role": current_user.role,
        }


@interview_access_router.get("/{interview_id}/candidate-info")
def get_interview_candidate_info(
    interview_id: int,
    current_user: User = Depends(require_roles("interviewer")),
):
    """Candidate CV highlights and profile for the assigned interviewer's room panel."""
    with SessionLocal() as session:
        row = session.execute(
            select(Interview, Application, Job, User)
            .join(Application, Application.id == Interview.application_id)
            .join(Job, Job.id == Application.job_id)
            .join(User, User.id == Application.candidate_id)
            .where(Interview.id == interview_id)
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Interview not found")
        interview, application, job, candidate = row
        if interview.interviewer_id != current_user.id:
            raise HTTPException(status_code=404, detail="Interview not found")

        profile = session.get(CandidateProfile, application.candidate_id)
        score = session.scalar(
            select(ScreeningScore)
            .where(ScreeningScore.application_id == application.id, ScreeningScore.status == "completed")
            .order_by(ScreeningScore.created_at.desc())
        )
        requirements = session.scalars(
            select(JobRequirement).where(JobRequirement.job_id == application.job_id)
        ).all()
        matched_names, unmet_names = set(), []
        if score and score.breakdown:
            for item in score.breakdown.get("requirements", []):
                if item.get("status") == "met":
                    matched_names.add(item.get("requirement"))
                elif item.get("status") in {"partially_met", "unmet"}:
                    unmet_names.append(item.get("requirement"))
        key_skills = [r.text for r in requirements if r.category == "skills" and r.text in matched_names]

        education = application.education_qualification or (profile.education_qualification if profile else None)
        institution = application.institution_name or (profile.institution_name if profile else None)
        graduation_year = profile.graduation_year if profile else None

        return {
            "candidate_name": application.candidate_name or (candidate.full_name if candidate else "Candidate"),
            "job_title": job.title,
            "seniority": job.seniority,
            "email": application.candidate_email or (profile.contact_email if profile else None),
            "phone": application.candidate_phone or (profile.phone_number if profile else None),
            "education": education,
            "institution": institution,
            "graduation_year": graduation_year,
            "pre_interview_score": score.total_score if score else None,
            "key_skills": key_skills,
            "areas_to_probe": unmet_names,
            "resume_available": bool(application.resume_storage_key),
        }


@interview_access_router.post("/{interview_id}/livekit-token")
def create_livekit_token(
    interview_id: int,
    current_user: User = Depends(require_roles("candidate", "interviewer")),
):
    from app.services import livekit_tokens

    if not livekit_tokens.is_configured():
        raise HTTPException(status_code=503, detail="LIVEKIT_NOT_CONFIGURED")
    with SessionLocal() as session:
        row = session.execute(
            select(Interview, Application, User)
            .join(Application, Application.id == Interview.application_id)
            .join(User, User.id == Application.candidate_id)
            .where(Interview.id == interview_id)
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Interview not found")
        interview, application, candidate = row
        has_access = (
            current_user.role == "candidate" and application.candidate_id == current_user.id
        ) or (
            current_user.role == "interviewer" and interview.interviewer_id == current_user.id
        )
        if not has_access:
            raise HTTPException(status_code=404, detail="Interview not found")
        if interview.status != "scheduled" or not _join_window_open(interview):
            raise HTTPException(status_code=409, detail="The interview room is available only shortly before the scheduled time")
        if current_user.role == "candidate":
            identity = f"candidate-{current_user.id}"
            display_name = application.candidate_name or candidate.full_name or "Candidate"
        else:
            identity = f"interviewer-{current_user.id}"
            display_name = current_user.full_name or "Interviewer"
        room_name = f"interview-{interview.id}"
    token = livekit_tokens.mint_token(identity=identity, name=display_name, room=room_name)
    return {
        "url": livekit_tokens.livekit_url(),
        "token": token,
        "room": room_name,
        "identity": identity,
    }


@interview_access_router.get("/{interview_id}/transcript")
def get_interview_transcript(
    interview_id: int,
    current_user: User = Depends(require_roles("hiring_manager", "interviewer")),
):
    with SessionLocal() as session:
        interview = session.get(Interview, interview_id)
        if interview is None or (current_user.role == "interviewer" and interview.interviewer_id != current_user.id):
            raise HTTPException(status_code=404, detail="Interview not found")
        segments = session.scalars(select(TranscriptSegment).where(
            TranscriptSegment.interview_id == interview_id
        ).order_by(TranscriptSegment.started_at_seconds, TranscriptSegment.id)).all()
        return [{
            "id": item.id, "speaker_role": item.speaker_role,
            "started_at_seconds": item.started_at_seconds,
            "ended_at_seconds": item.ended_at_seconds, "text": item.text,
        } for item in segments]


@interview_access_router.websocket("/{interview_id}/transcript")
async def interview_transcript(websocket: WebSocket, interview_id: int):
    token = websocket.cookies.get("access_token")
    if not token:
        await websocket.close(code=4401)
        return
    try:
        from app.services.security import decode_access_token
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except Exception:
        await websocket.close(code=4401)
        return
    with SessionLocal() as session:
        user = session.get(User, user_id)
        row = session.execute(select(Interview, Application).join(
            Application, Application.id == Interview.application_id
        ).where(Interview.id == interview_id)).first()
        if user is None or not user.is_active or row is None:
            await websocket.close(code=4404)
            return
        interview, application = row
        if user.role == "candidate" and application.candidate_id == user.id:
            role = "candidate"
        elif user.role == "interviewer" and interview.interviewer_id == user.id:
            role = "interviewer"
        else:
            await websocket.close(code=4403)
            return
        if interview.status != "scheduled" or not _join_window_open(interview):
            await websocket.close(code=4403)
            return
    await websocket.accept()
    room = _transcript_sockets.setdefault(interview_id, {})
    old = room.get(role)
    if old is not None:
        # A previous socket for this role is still registered (a reload, a reconnect,
        # or an abrupt tab close that the server hasn't detected yet). Evict it so the
        # new connection takes over, instead of rejecting the new one and leaving
        # transcription permanently stuck for this role until the API restarts.
        try:
            await old.close(code=4409)
        except Exception:
            pass
    room[role] = websocket
    try:
        consent = await websocket.receive_json()
        if not isinstance(consent, dict) or consent.get("type") != "consent" or consent.get("consent") is not True:
            await websocket.close(code=4403)
            return
        mime_type = consent.get("mime_type", "audio/webm")
        supported_mime_types = {
            "audio/webm", "audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4",
        }
        if mime_type not in supported_mime_types:
            await websocket.close(code=4400)
            return
        provider_mime_type = mime_type.split(";", 1)[0]
        with SessionLocal() as session:
            record = session.scalar(select(InterviewConsent).where(
                InterviewConsent.interview_id == interview_id,
                InterviewConsent.user_id == user_id,
                InterviewConsent.consent_type == "audio_transcription",
            ))
            if record:
                record.revoked_at = None
            else:
                session.add(InterviewConsent(
                    interview_id=interview_id, user_id=user_id,
                    consent_type="audio_transcription",
                ))
            session.commit()
        await websocket.send_json({"type": "transcription_ready"})
        while True:
            audio = await websocket.receive_bytes()
            logging.getLogger(__name__).info(
                "TRANSCRIPT chunk received: interview=%s role=%s bytes=%s",
                interview_id, role, len(audio) if audio else 0,
            )
            if not audio or len(audio) > 2 * 1024 * 1024:
                await websocket.send_json({"type": "transcription_error", "message": "Audio chunk is empty or too large."})
                continue
            ended = datetime.now(timezone.utc)
            with SessionLocal() as session:
                started_at = session.get(Interview, interview_id).started_at
            offset_end = max(0.0, (ended - (started_at or ended)).total_seconds())
            try:
                text = await transcribe_audio_chunk(audio, mime_type=provider_mime_type)
            except Exception:
                logging.getLogger(__name__).exception(
                    "Transcription failed for interview %s (mime=%s, bytes=%s)",
                    interview_id, provider_mime_type, len(audio),
                )
                await websocket.send_json({"type": "transcription_error", "message": "Transcription is temporarily unavailable."})
                continue
            finally:
                del audio
            logging.getLogger(__name__).info(
                "TRANSCRIPT result: interview=%s role=%s chars=%s text=%r",
                interview_id, role, len(text), text[:80],
            )
            if not text:
                continue
            segment_data = {
                "interview_id": interview_id, "speaker_role": role,
                "started_at_seconds": max(0.0, offset_end - 4.0),
                "ended_at_seconds": offset_end, "text": text, "source": "gemini_audio",
            }
            with SessionLocal() as session:
                segment = TranscriptSegment(**segment_data)
                session.add(segment)
                session.commit()
                session.refresh(segment)
                message = {"type": "transcript", "segment": {
                    "id": segment.id, "speaker_role": role,
                    "started_at_seconds": segment.started_at_seconds,
                    "ended_at_seconds": segment.ended_at_seconds, "text": text,
                }}
            for peer in list(room.values()):
                try:
                    await peer.send_json(message)
                except Exception:
                    pass
    except WebSocketDisconnect:
        pass
    finally:
        with SessionLocal() as session:
            record = session.scalar(select(InterviewConsent).where(
                InterviewConsent.interview_id == interview_id,
                InterviewConsent.user_id == user_id,
                InterviewConsent.consent_type == "audio_transcription",
            ))
            if record and record.revoked_at is None:
                record.revoked_at = datetime.now(timezone.utc)
                session.commit()
        # Only remove our own slot: if a newer socket already replaced us, leave it.
        if room.get(role) is websocket:
            room.pop(role, None)
        if not room:
            _transcript_sockets.pop(interview_id, None)


@interview_access_router.websocket("/{interview_id}/signal")
async def interview_signal(websocket: WebSocket, interview_id: int):
    token = websocket.cookies.get("access_token")
    if not token:
        await websocket.close(code=4401)
        return
    try:
        from app.services.security import decode_access_token
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except Exception:
        await websocket.close(code=4401)
        return
    with SessionLocal() as session:
        user = session.get(User, user_id)
        row = session.execute(
            select(Interview, Application)
            .join(Application, Application.id == Interview.application_id)
            .where(Interview.id == interview_id)
        ).first()
        if user is None or not user.is_active or row is None:
            await websocket.close(code=4404)
            return
        interview, application = row
        if user.role == "candidate":
            role = "candidate" if application.candidate_id == user.id else None
        elif user.role == "interviewer":
            role = "interviewer" if interview.interviewer_id == user.id else None
        else:
            role = None
        if not role or interview.status != "scheduled" or not _join_window_open(interview):
            await websocket.close(code=4403)
            return

    await websocket.accept()
    if role == "candidate":
        with SessionLocal() as session:
            live_interview = session.scalar(
                select(Interview)
                .where(Interview.id == interview_id)
                .with_for_update()
            )
            if (
                live_interview
                and live_interview.status == "scheduled"
                and live_interview.candidate_joined_at is None
            ):
                live_interview.candidate_joined_at = datetime.now(timezone.utc)
                session.commit()
    room = _room_sockets.setdefault(interview_id, {})
    old = room.get(role)
    if old is not None:
        # Evict a stale socket for this role so a reconnecting participant can rejoin.
        try:
            await old.close(code=4409)
        except Exception:
            pass
    room[role] = websocket
    if "candidate" in room and "interviewer" in room:
        with SessionLocal() as session:
            live_interview = session.get(Interview, interview_id)
            if live_interview and live_interview.started_at is None:
                live_interview.started_at = datetime.now(timezone.utc)
                session.commit()
        for peer in room.values():
            await peer.send_json({"type": "ready"})
    identity_frame_checked = False
    try:
        while True:
            message = await websocket.receive_json()
            if not isinstance(message, dict) or message.get("type") not in {"offer", "answer", "ice", "end", "identity_frame", "identity_consent"}:
                continue
            if message["type"] == "identity_consent":
                if role != "candidate" or not isinstance(message.get("consent"), bool):
                    continue
                with SessionLocal() as session:
                    record = session.scalar(select(InterviewConsent).where(
                        InterviewConsent.interview_id == interview_id,
                        InterviewConsent.user_id == user_id,
                        InterviewConsent.consent_type == "biometric_match",
                    ))
                    if message["consent"]:
                        if record is None:
                            record = InterviewConsent(interview_id=interview_id, user_id=user_id,
                                consent_type="biometric_match", consented_at=datetime.now(timezone.utc))
                            session.add(record)
                        else:
                            record.consented_at = datetime.now(timezone.utc)
                            record.revoked_at = None
                    elif record and record.revoked_at is None:
                        record.revoked_at = datetime.now(timezone.utc)
                    session.commit()
                continue
            if message["type"] == "identity_frame":
                if role != "candidate":
                    continue
                if identity_frame_checked:
                    await websocket.send_json({"type": "identity_result", "matched": False, "reason": "already_checked"})
                    continue
                identity_frame_checked = True
                data_url = message.get("data")
                encoded = data_url.split(",", 1)[-1] if isinstance(data_url, str) else ""
                if len(encoded) > MAX_IMAGE_BYTES * 2:
                    await websocket.send_json({"type": "identity_result", "matched": False, "reason": "frame_too_large"})
                    continue
                try:
                    frame = base64.b64decode(encoded, validate=True)
                    with SessionLocal() as session:
                        consent = session.scalar(select(InterviewConsent).where(
                            InterviewConsent.interview_id == interview_id,
                            InterviewConsent.user_id == user_id,
                            InterviewConsent.consent_type == "biometric_match",
                            InterviewConsent.revoked_at.is_(None),
                        ))
                        enrollment = session.get(BiometricEnrollment, application.candidate_id)
                        if not consent:
                            identity = {"matched": False, "reason": "no_interview_consent"}
                        elif not enrollment or enrollment.revoked_at is not None or enrollment.retention_until <= datetime.now(timezone.utc):
                            identity = {"matched": False, "reason": "no_active_consent"}
                        else:
                            matched, _score = compare_embedding(frame, enrollment.embedding)
                            identity = {"matched": matched, "reason": "match" if matched else "no_match"}
                            if matched:
                                candidate = session.get(User, application.candidate_id)
                                profile = session.get(CandidateProfile, application.candidate_id)
                                score = session.scalar(select(ScreeningScore).where(
                                    ScreeningScore.application_id == application.id,
                                    ScreeningScore.status == "completed"
                                ).order_by(ScreeningScore.created_at.desc()))
                                requirements = session.scalars(select(JobRequirement).where(
                                    JobRequirement.job_id == application.job_id
                                )).all()
                                matched_names, unmet_names = set(), []
                                if score and score.breakdown:
                                    for item in score.breakdown.get("requirements", []):
                                        if item.get("status") == "met":
                                            matched_names.add(item.get("requirement"))
                                        elif item.get("status") in {"partially_met", "unmet"}:
                                            unmet_names.append(item.get("requirement"))
                                identity["profile"] = {
                                    "candidate_name": application.candidate_name or (candidate.full_name if candidate else "Candidate"),
                                    "headline_experience": application.education_qualification or (profile.education_qualification if profile else None),
                                    "key_skills": [r.text for r in requirements if r.category == "skills" and r.text in matched_names],
                                    "pre_interview_score": score.total_score if score else None,
                                    "areas_to_probe": unmet_names,
                                }
                    await websocket.send_json({"type": "identity_result", **identity})
                    if identity.get("matched") and room.get("interviewer"):
                        await room["interviewer"].send_json({"type": "identity_result", **identity})
                except (binascii.Error, ValueError, RuntimeError):
                    await websocket.send_json({"type": "identity_result", "matched": False, "reason": "frame_invalid"})
                continue
            if message["type"] == "end":
                with SessionLocal() as session:
                    completed_row = session.execute(
                        select(Interview, Application, User)
                        .join(Application, Application.id == Interview.application_id)
                        .join(User, User.id == Application.candidate_id)
                        .where(Interview.id == interview_id)
                    ).first()
                    if completed_row:
                        ended, application, candidate = completed_row
                        if ended.status != "completed":
                            ended.ended_at = datetime.now(timezone.utc)
                            ended.status = "completed"
                            ended.analysis_status = "pending"
                            ended.analysis_attempts = 0
                            ended.analysis_processing_at = None
                            ended.analysis_next_attempt_at = datetime.now(timezone.utc)
                            ended.analysis_error_code = None
                            application.status = "interview completed"
                            queue_status_email(session, application, application.candidate_email or candidate.email,
                                               "interview completed", event_key=f"interview-completed:{interview_id}")
                        session.commit()
                for peer in list(room.values()):
                    if peer is not websocket:
                        await peer.send_json({"type": "end"})
                break
            peer = room.get("interviewer" if role == "candidate" else "candidate")
            if peer:
                await peer.send_json({"type": message["type"], "data": message.get("data")})
    except WebSocketDisconnect:
        pass
    finally:
        if role == "candidate":
            with SessionLocal() as session:
                record = session.scalar(select(InterviewConsent).where(
                    InterviewConsent.interview_id == interview_id,
                    InterviewConsent.user_id == user_id,
                    InterviewConsent.consent_type == "biometric_match",
                ))
                if record and record.revoked_at is None:
                    record.revoked_at = datetime.now(timezone.utc)
                    session.commit()
        # Only remove our own slot: if a newer socket already replaced us, leave it.
        if room.get(role) is websocket:
            room.pop(role, None)
        if not room:
            _room_sockets.pop(interview_id, None)
