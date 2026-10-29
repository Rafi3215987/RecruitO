import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy import and_, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.db.session import SessionLocal
from app.dependencies import require_roles
from app.graphs.application_ranking_graph import application_ranking_graph
from app.models.application import Application
from app.models.interview import Interview
from app.models.job import Job
from app.models.user import CandidateProfile, User
from app.models.audit_log import AuditLog
from app.models.notification import Notification
from app.models.screening_score import ScreeningScore, InterviewEvaluation
from app.schemas.application import (
    ApplicationSubmittedResponse,
    CandidateApplicationSubmission,
    CandidateApplicationItem,
    HiringManagerApplicationItem,
    ManagerCandidateCorrection,
    ManagerApplicationStatusChange,
    ManagerActionReason,
    FinalizeJobSelection,
)
from app.services.assessment import build_consolidated_assessment
from app.services.cv_import import (
    MAX_FILES_PER_REQUEST,
    MAX_RESUME_BYTES,
    ResumeUploadError,
    import_resume_file,
    validate_resume_upload,
)
from app.services.notifications import queue_email, queue_status_email
from app.services.screening_queue import enqueue_application_screening, requirement_data_for_job


router = APIRouter(prefix="/public/jobs", tags=["applications"])
candidate_router = APIRouter(prefix="/me", tags=["candidate dashboard"])
manager_router = APIRouter(prefix="/applications", tags=["hiring manager applications"])
god_mode_router = APIRouter(prefix="/admin/applications", tags=["hiring manager god mode"])
god_mode_candidate_router = APIRouter(prefix="/admin/candidates", tags=["hiring manager god mode"])


ranking_router = APIRouter(prefix="/jobs", tags=["screening and ranking"])
logger = logging.getLogger(__name__)
UPLOAD_DIR = Path(os.getenv("CANDIDATE_UPLOAD_DIR", "/data/candidate-resumes"))


@manager_router.get("", response_model=list[HiringManagerApplicationItem])
def list_applications_for_hiring_manager(
    _current_user: User = Depends(require_roles("hiring_manager")),
):
    with SessionLocal() as session:
        rows = session.execute(
            select(Application, Job, User, CandidateProfile, Interview)
            .join(Job, Job.id == Application.job_id)
            .join(User, User.id == Application.candidate_id)
            .outerjoin(CandidateProfile, CandidateProfile.user_id == User.id)
            .outerjoin(
                Interview,
                and_(
                    Interview.application_id == Application.id,
                    Interview.manager_removed_at.is_(None),
                ),
            )
            .order_by(Application.created_at.desc())
        ).all()

        application_ids = [application.id for application, *_ in rows]
        latest_scores = {}
        if application_ids:
            score_rows = session.scalars(
                select(ScreeningScore)
                .where(ScreeningScore.application_id.in_(application_ids))
                .order_by(ScreeningScore.created_at.desc(), ScreeningScore.id.desc())
            ).all()
            for score in score_rows:
                latest_scores.setdefault(score.application_id, score)

        return [
            HiringManagerApplicationItem(
                id=application.id,
                interview_id=(interview.id if interview else None),
                job_id=job.id,
                candidate_name=(application.candidate_name or (
                    profile.certificate_full_name
                    if profile and profile.certificate_full_name
                    else candidate.full_name
                )),
                candidate_email=(
                    application.candidate_email
                    or (profile.contact_email
                    if profile and profile.contact_email
                    else candidate.email)
                ),
                candidate_phone=application.candidate_phone or (profile.phone_number if profile else None),
                education_qualification=application.education_qualification or (profile.education_qualification if profile else None),
                institution_name=application.institution_name or (profile.institution_name if profile else None),
                department=application.department or (profile.department if profile else None),
                graduation_year=application.graduation_year or (profile.graduation_year if profile else None),
                resume_file_name=application.resume_file_name or (profile.resume_file_name if profile else None),
                job_title=job.title,
                status=application.status,
                applied_at=application.created_at,
                score_status=(latest_scores[application.id].status if application.id in latest_scores else "not_started"),
                total_score=(latest_scores[application.id].total_score if application.id in latest_scores else None),
                score_error_code=(latest_scores[application.id].error_code if application.id in latest_scores else None),
                interview_scheduled_at=(
                    interview.scheduled_at if interview else None
                ),
                interview_duration_minutes=(
                    interview.duration_minutes if interview else None
                ),
                interview_ended_at=(interview.ended_at if interview else None),
                interview_status=(interview.status if interview else None),
                interviewer_id=(interview.interviewer_id if interview else None),
                join_available=bool(
                    interview and interview.status == "scheduled"
                    and interview.scheduled_at - timedelta(minutes=15)
                    <= datetime.now(timezone.utc)
                    <= interview.scheduled_at + timedelta(minutes=interview.duration_minutes + 30)
                ),
                interview_analysis_status=(interview.analysis_status if interview else "not_started"),
                interview_analysis_error_code=(interview.analysis_error_code if interview else None),
                interview_scheduling_status=application.scheduling_status,
                interview_scheduling_error_code=application.scheduling_error_code,
            )
            for application, job, candidate, profile, interview in rows
        ]


def _candidate_status(internal_status: str) -> str:
    normalized = internal_status.strip().lower().replace("_", " ")
    if normalized == "withdrawn":
        return "Withdrawn"
    if normalized in {"submitted", "pending", "parsing", "screening", "ranked"}:
        return "Under review"
    if normalized in {"selected for interview", "interview stage"}:
        return "Interview stage"
    if normalized in {"not selected", "rejected"}:
        return "Not selected"
    if normalized == "selected":
        return "Selected"
    if normalized == "interview scheduled":
        return "Interview scheduled"
    if normalized == "interview completed":
        return "Awaiting decision"
    if normalized in {"decision made", "decision available"}:
        return "Decision available"
    return "Under review"


@candidate_router.get(
    "/applications",
    response_model=list[CandidateApplicationItem],
)
def list_my_applications(
    current_user: User = Depends(require_roles("candidate")),
):
    with SessionLocal() as session:
        rows = session.execute(
            select(Application, Job, Interview)
            .join(Job, Job.id == Application.job_id)
            .outerjoin(
                Interview,
                Interview.application_id == Application.id,
            )
            .where(
                Application.candidate_id == current_user.id,
                Application.candidate_removed_at.is_(None),
            )
            .order_by(Application.created_at.desc())
        ).all()

        applications = [
            CandidateApplicationItem(
                id=application.id,
                interview_id=(interview.id if interview else None),
                job_id=job.id,
                job_title=job.title,
                seniority=job.seniority,
                applied_at=application.created_at,
                status=_candidate_status(application.status),
                interview_scheduled_at=(
                    interview.scheduled_at if interview else None
                ),
                interview_duration_minutes=(
                    interview.duration_minutes if interview else None
                ),
                interview_scheduling_status=application.scheduling_status,
                interview_scheduling_error_code=application.scheduling_error_code,
                join_available=bool(
                    interview and interview.status == "scheduled"
                    and interview.scheduled_at - timedelta(minutes=15)
                    <= datetime.now(timezone.utc)
                    <= interview.scheduled_at + timedelta(minutes=interview.duration_minutes + 30)
                ),
            )
            for application, job, interview in rows
        ]
        return sorted(
            applications,
            key=lambda item: (
                item.interview_scheduled_at is None,
                item.interview_scheduled_at or item.applied_at,
            ),
        )


@candidate_router.delete("/applications/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_my_application(
    application_id: int,
    current_user: User = Depends(require_roles("candidate")),
):
    with SessionLocal() as session:
        row = session.execute(
            select(Application, Job, Interview)
            .join(Job, Job.id == Application.job_id)
            .outerjoin(Interview, Interview.application_id == Application.id)
            .where(
                Application.id == application_id,
                Application.candidate_id == current_user.id,
            )
            .with_for_update(of=Application)
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Application not found")

        application, job, interview = row
        if application.candidate_removed_at is not None:
            return

        previous_status = application.status
        application.candidate_removed_at = datetime.now(timezone.utc)
        application.status = "withdrawn"
        application.scheduling_status = "cancelled"
        application.scheduling_processing_at = None
        application.scheduling_next_attempt_at = None

        if interview and interview.status == "scheduled":
            interview.status = "cancelled"
            interview.cancellation_reason = "Candidate withdrew the application"
            interview.token_hash = None
            interview.token_expires_at = None
            interview.interviewer_token_hash = None
            interview.interviewer_token_expires_at = None
            session.execute(
                update(Notification)
                .where(
                    Notification.application_id == application.id,
                    Notification.status_key.like(f"interviewer-reminder:{interview.id}:%"),
                    Notification.state.in_(("pending", "failed", "sending")),
                )
                .values(
                    state="cancelled",
                    recipient_email="",
                    body="",
                    payload=None,
                    available_at=None,
                )
            )
            interviewer = session.get(User, interview.interviewer_id) if interview.interviewer_id else None
            if interviewer and interviewer.is_active:
                queue_email(
                    session,
                    application_id=application.id,
                    recipient=interviewer.email,
                    status_key=f"interviewer-application-withdrew:{application.id}",
                    subject=f"Interview cancelled: {job.title}",
                    body=f"The candidate withdrew their application for {job.title}; the scheduled interview has been cancelled.",
                )

        session.add(AuditLog(
            actor_user_id=current_user.id,
            action="candidate_withdrew_application",
            target_type="application",
            target_id=str(application.id),
            before_values={"status": previous_status, "job_title": job.title},
            after_values={"status": "withdrawn", "candidate_removed": True},
            reason="Candidate removed this application from their dashboard.",
        ))
        queue_email(
            session,
            application_id=application.id,
            recipient=application.candidate_email or current_user.email,
            status_key=f"candidate-withdrew-confirmation:{application.id}",
            subject=f"Application withdrawn: {job.title}",
            body=(
                f"Your application for {job.title} has been withdrawn and is no longer shown in your dashboard. "
                "RecruitO retains the application and assessment history for the hiring team."
            ),
        )
        if job.created_by_id:
            manager = session.get(User, job.created_by_id)
            if manager and manager.role == "hiring_manager" and manager.is_active:
                queue_email(
                    session,
                    application_id=application.id,
                    recipient=manager.email,
                    status_key=f"manager-candidate-withdrew:{application.id}",
                    subject=f"Candidate withdrew from {job.title}",
                    body=(
                        f"{application.candidate_name or 'A candidate'} withdrew an application for {job.title}. "
                        "Sign in to review its updated status."
                    ),
                )
        session.commit()


@router.post(
    "/{job_id}/apply",
    response_model=ApplicationSubmittedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_application(
    job_id: int,
    full_name: str = Form(...),
    email: str = Form(...),
    phone_number: str = Form(...),
    education_qualification: str = Form(...),
    institution_name: str = Form(...),
    department: str = Form(...),
    graduation_year: str | None = Form(default=None),
    resume_file: UploadFile = File(...),
    current_user: User = Depends(require_roles("candidate")),
):
    try:
        request = CandidateApplicationSubmission(
            full_name=full_name,
            email=email,
            phone_number=phone_number,
            education_qualification=education_qualification,
            institution_name=institution_name,
            department=department,
            graduation_year=graduation_year,
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors(include_input=False)) from exc

    content = await resume_file.read(MAX_RESUME_BYTES + 1)
    try:
        safe_name, extension = validate_resume_upload(resume_file.filename, content)
    except ResumeUploadError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    storage_key = f"{uuid.uuid4().hex}{extension}"
    stored_path = UPLOAD_DIR / storage_key
    with SessionLocal() as session:
        job = session.scalar(
            select(Job).where(
                Job.id == job_id,
                Job.status == "approved",
            ).with_for_update()
        )
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found",
            )

        existing = session.scalar(
            select(Application).where(
                Application.candidate_id == current_user.id,
                Application.job_id == job_id,
            )
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already applied to this job",
            )

        candidate = session.scalar(
            select(User).options(selectinload(User.candidate_profile)).where(User.id == current_user.id)
        )
        if candidate is None or candidate.candidate_profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate profile not found",
            )

        profile = candidate.candidate_profile
        profile.contact_email = str(request.email)
        profile.phone_number = request.phone_number.strip()
        profile.certificate_full_name = request.full_name.strip()
        profile.education_qualification = request.education_qualification.strip()
        profile.institution_name = request.institution_name.strip()
        profile.department = request.department.strip()
        profile.graduation_year = request.graduation_year
        profile.resume_storage_key = storage_key
        profile.resume_file_name = safe_name

        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        stored_path.write_bytes(content)

        application = Application(
            candidate_id=current_user.id,
            job_id=job_id,
            candidate_name=request.full_name.strip(),
            candidate_email=str(request.email),
            candidate_phone=request.phone_number.strip(),
            education_qualification=request.education_qualification.strip(),
            institution_name=request.institution_name.strip(),
            department=request.department.strip(),
            graduation_year=request.graduation_year,
            resume_storage_key=storage_key,
            resume_file_name=safe_name,
            scheduling_status="not_queued",
        )
        session.add(application)
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            stored_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already applied to this job",
            )

        queued_score = enqueue_application_screening(
            session,
            application,
            content,
            requirement_data_for_job(session, job.id),
            job.jd_text or "",
        )
        application_copy = "\n".join([
            "Application details you submitted:",
            f"Name: {application.candidate_name}",
            f"Email: {application.candidate_email}",
            f"Phone: {application.candidate_phone}",
            f"Education: {application.education_qualification}",
            f"Institution: {application.institution_name}",
            f"Major: {application.department}",
            f"Graduation year: {application.graduation_year or 'Not provided'}",
            f"CV file: {application.resume_file_name}",
        ])
        queue_email(
            session,
            application_id=application.id,
            recipient=str(request.email),
            status_key="application-received",
            subject=f"We received your application: {job.title}",
            body=(
                f"Thank you for applying for {job.title}. Your application has been received and is now under review. "
                f"Your reference number is {application.id}. We will email you when your application status changes.\n\n"
                f"{application_copy}"
            ),
        )

        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            stored_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already applied to this job",
            )
        except Exception:
            session.rollback()
            stored_path.unlink(missing_ok=True)
            raise

        session.refresh(application)
        session.expunge(application)
        result = application
        score_status = queued_score.status
    return ApplicationSubmittedResponse(
        id=result.id,
        job_id=result.job_id,
        status=result.status,
        created_at=result.created_at,
        confirmation_email_queued=True,
        score_status=score_status,
        scheduling_status=result.scheduling_status,
    )


@manager_router.get("/{application_id}/resume")
def download_application_resume(
    application_id: int,
    _current_user: User = Depends(require_roles("hiring_manager")),
):
    with SessionLocal() as session:
        application = session.scalar(
            select(Application).where(Application.id == application_id)
        )
        if application is None or not application.resume_storage_key:
            raise HTTPException(status_code=404, detail="Resume not found")
        storage_key = application.resume_storage_key
        file_name = application.resume_file_name or "resume"

    path = UPLOAD_DIR / storage_key
    if not path.is_file() or path.parent.resolve() != UPLOAD_DIR.resolve():
        raise HTTPException(status_code=404, detail="Resume not found")
    return FileResponse(
        path,
        filename=file_name,
        media_type="application/octet-stream",
    )


@god_mode_router.patch("/{application_id}/correction", response_model=HiringManagerApplicationItem)
def correct_candidate_application(
    application_id: int,
    request: ManagerCandidateCorrection,
    actor: User = Depends(require_roles("hiring_manager")),
):
    updates = request.model_dump(exclude={"reason"}, exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="Provide at least one field to correct")
    with SessionLocal() as session:
        row = session.execute(
            select(Application, Job, User, CandidateProfile, Interview)
            .join(Job, Job.id == Application.job_id)
            .join(User, User.id == Application.candidate_id)
            .outerjoin(CandidateProfile, CandidateProfile.user_id == User.id)
            .outerjoin(Interview, Interview.application_id == Application.id)
            .where(Application.id == application_id)
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Application not found")
        application, job, candidate, profile, interview = row
        before = {}
        after = {}
        mapping = {
            "full_name": ("candidate_name", "certificate_full_name"),
            "email": ("candidate_email", "contact_email"),
            "phone_number": ("candidate_phone", "phone_number"),
            "education_qualification": ("education_qualification", "education_qualification"),
            "institution_name": ("institution_name", "institution_name"),
            "department": ("department", "department"),
            "graduation_year": ("graduation_year", "graduation_year"),
        }
        for field, value in updates.items():
            app_field, profile_field = mapping[field]
            prior = getattr(application, app_field)
            if prior is None and profile is not None:
                prior = getattr(profile, profile_field)
            before[field] = prior
            normalized = str(value) if field == "email" and value is not None else value
            if isinstance(normalized, str):
                normalized = normalized.strip()
                if not normalized:
                    raise HTTPException(status_code=422, detail=f"{field} cannot be blank")
            setattr(application, app_field, normalized)
            if profile is not None:
                setattr(profile, profile_field, normalized)
            if field == "full_name":
                candidate.full_name = normalized
            if field == "email":
                candidate.email = normalized
            after[field] = normalized
        audit = AuditLog(
            actor_user_id=actor.id, action="correct_candidate_application",
            target_type="application", target_id=str(application.id),
            before_values=before, after_values=after, reason=request.reason,
        )
        session.add(audit)
        session.flush()
        recipient = application.candidate_email or candidate.email
        queue_email(
            session, application_id=application.id, recipient=recipient,
            status_key=f"candidate-correction:{audit.id}",
            subject="Your application information was updated",
            body="The hiring team corrected information on your application. Sign in to RecruitO to review your profile and contact the team if anything still looks wrong.",
        )
        session.commit()
        return HiringManagerApplicationItem(
            id=application.id, job_id=job.id, candidate_name=application.candidate_name or candidate.full_name,
            candidate_email=application.candidate_email or candidate.email,
            candidate_phone=application.candidate_phone, education_qualification=application.education_qualification,
            institution_name=application.institution_name, department=application.department,
            graduation_year=application.graduation_year, resume_file_name=application.resume_file_name,
            job_title=job.title, status=application.status, applied_at=application.created_at,
            interview_scheduled_at=interview.scheduled_at if interview else None,
            interview_duration_minutes=interview.duration_minutes if interview else None,
            interviewer_id=interview.interviewer_id if interview else None,
            interview_analysis_status=interview.analysis_status if interview else "not_started",
            interview_analysis_error_code=interview.analysis_error_code if interview else None,
            interview_scheduling_status=application.scheduling_status,
            interview_scheduling_error_code=application.scheduling_error_code,
        )


@god_mode_router.patch("/{application_id}/status")
def change_application_status(
    application_id: int,
    request: ManagerApplicationStatusChange,
    actor: User = Depends(require_roles("hiring_manager")),
):
    internal_status = {
        "under review": "submitted",
        "interview stage": "selected for interview",
        "not selected": "not selected",
        "interview scheduled": "interview scheduled",
        "awaiting decision": "interview completed",
        "decision available": "decision available",
    }[request.status]
    with SessionLocal() as session:
        row = session.execute(
            select(Application, User).join(User, User.id == Application.candidate_id)
            .where(Application.id == application_id)
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Application not found")
        application, candidate = row
        old_status = application.status
        if old_status == internal_status:
            return {"id": application.id, "status": _candidate_status(old_status), "changed": False}
        application.status = internal_status
        if internal_status != "selected for interview" and application.scheduling_status in {"pending", "manager_notified"}:
            application.scheduling_status = "cancelled"
            application.scheduling_processing_at = None
            application.scheduling_next_attempt_at = None
            application.scheduling_error_code = None
        audit = AuditLog(
            actor_user_id=actor.id, action="change_application_status",
            target_type="application", target_id=str(application.id),
            before_values={"status": old_status}, after_values={"status": internal_status},
            reason=request.reason,
        )
        session.add(audit)
        session.flush()
        queue_status_email(
            session, application, application.candidate_email or candidate.email,
            internal_status, event_key=str(audit.id),
        )
        session.commit()
        return {"id": application.id, "status": request.status.title(), "changed": True}


@god_mode_candidate_router.delete("/{candidate_id}", status_code=204)
def delete_candidate_data(
    candidate_id: int,
    reason: str,
    actor: User = Depends(require_roles("hiring_manager")),
):
    cleaned_reason = reason.strip()
    if len(cleaned_reason) < 10 or len(cleaned_reason) > 1000:
        raise HTTPException(status_code=422, detail="Reason must contain 10 to 1000 characters")
    with SessionLocal() as session:
        candidate = session.scalar(select(User).where(User.id == candidate_id, User.role == "candidate"))
        if candidate is None:
            raise HTTPException(status_code=404, detail="Candidate not found")
        applications = session.scalars(select(Application).where(Application.candidate_id == candidate_id)).all()
        application_ids = [str(item.id) for item in applications]
        keys = {item.resume_storage_key for item in applications if item.resume_storage_key}
        if candidate.candidate_profile and candidate.candidate_profile.resume_storage_key:
            keys.add(candidate.candidate_profile.resume_storage_key)
        session.add(AuditLog(
            actor_user_id=actor.id, action="delete_candidate_data", target_type="candidate",
            target_id=str(candidate_id), before_values={"application_count": len(applications)},
            after_values={"deleted": True}, reason=cleaned_reason,
        ))
        personal_audits = session.scalars(select(AuditLog).where(
            ((AuditLog.target_type == "candidate") & (AuditLog.target_id == str(candidate_id)))
            | ((AuditLog.target_type == "application") & (AuditLog.target_id.in_(application_ids if application_ids else ["-1"])))
        )).all()
        for entry in personal_audits:
            entry.before_values = None
            entry.after_values = None
        session.delete(candidate)
        session.commit()
    for key in keys:
        path = UPLOAD_DIR / key
        if path.parent.resolve() == UPLOAD_DIR.resolve():
            path.unlink(missing_ok=True)
    return None


def _requeue_application_score(session, application: Application, job: Job) -> dict:
    """Queue a score for the current CV and job inputs, keeping earlier versions.

    Identical inputs reuse the stored score, since reproducibility means
    a rescore of unchanged inputs must not produce a different verdict.
    """
    path = UPLOAD_DIR / (application.resume_storage_key or "")
    if (
        not application.resume_storage_key
        or not path.is_file()
        or path.parent.resolve() != UPLOAD_DIR.resolve()
    ):
        return {"application_id": application.id, "outcome": "resume_missing", "score_status": None}
    content = path.read_bytes()
    before = session.scalar(
        select(ScreeningScore)
        .where(ScreeningScore.application_id == application.id)
        .order_by(ScreeningScore.created_at.desc(), ScreeningScore.id.desc())
        .limit(1)
    )
    prior_status = before.status if before else None
    score = enqueue_application_screening(
        session,
        application,
        content,
        requirement_data_for_job(session, job.id),
        job.jd_text or "",
    )
    session.flush()
    if before is None or score.id != before.id:
        outcome = "queued_new_version"
    elif prior_status == "failed" and score.status == "pending":
        outcome = "retrying"
    elif score.status == "completed":
        outcome = "unchanged_inputs"
    else:
        outcome = "already_in_progress"
    return {"application_id": application.id, "outcome": outcome, "score_id": score.id,
            "score_status": score.status}


@god_mode_router.post("/{application_id}/rescore")
def rescore_application(
    application_id: int,
    request: ManagerActionReason,
    actor: User = Depends(require_roles("hiring_manager")),
):
    """Re-run screening against the job's current requirements; scores are never edited directly."""
    with SessionLocal() as session:
        application = session.get(Application, application_id)
        if application is None:
            raise HTTPException(status_code=404, detail="Application not found")
        job = session.get(Job, application.job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        result = _requeue_application_score(session, application, job)
        if result["outcome"] == "resume_missing":
            raise HTTPException(status_code=409, detail="This application has no readable CV to score")
        session.add(AuditLog(
            actor_user_id=actor.id, action="rescore_application", target_type="application",
            target_id=str(application.id), before_values=None,
            after_values={"outcome": result["outcome"], "score_id": result["score_id"]},
            reason=request.reason,
        ))
        session.commit()
        return result


@ranking_router.post("/{job_id}/rescore")
def rescore_job_applications(
    job_id: int,
    request: ManagerActionReason,
    actor: User = Depends(require_roles("hiring_manager")),
):
    """Rescore every active application, for example after the job requirements were edited."""
    with SessionLocal() as session:
        job = session.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        applications = session.scalars(
            select(Application)
            .where(Application.job_id == job_id, Application.status != "withdrawn")
            .order_by(Application.created_at, Application.id)
        ).all()
        results = [_requeue_application_score(session, application, job) for application in applications]
        session.add(AuditLog(
            actor_user_id=actor.id, action="rescore_job_applications", target_type="job",
            target_id=str(job_id), before_values=None,
            after_values={"applications": len(results),
                          "queued": sum(1 for item in results if item["outcome"] in {"queued_new_version", "retrying"})},
            reason=request.reason,
        ))
        session.commit()
    return {"job_id": job_id, "results": results}


@ranking_router.get("/{job_id}/rescore-progress")
def rescore_progress(
    job_id: int,
    actor: User = Depends(require_roles("hiring_manager")),
):
    """Report how many applicants have finished (re)scoring, for a progress bar."""
    with SessionLocal() as session:
        job = session.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        applications = session.scalars(
            select(Application).where(
                Application.job_id == job_id, Application.status != "withdrawn"
            )
        ).all()
        total = len(applications)

        status_by_app: dict[int, str] = {}
        if applications:
            app_ids = [a.id for a in applications]
            ranked = (
                select(
                    ScreeningScore.application_id.label("application_id"),
                    ScreeningScore.status.label("status"),
                    func.row_number()
                    .over(
                        partition_by=ScreeningScore.application_id,
                        order_by=(ScreeningScore.created_at.desc(), ScreeningScore.id.desc()),
                    )
                    .label("rn"),
                )
                .where(ScreeningScore.application_id.in_(app_ids))
                .subquery()
            )
            for app_id, score_status in session.execute(
                select(ranked.c.application_id, ranked.c.status).where(ranked.c.rn == 1)
            ).all():
                status_by_app[app_id] = score_status

        completed = failed = pending = processing = 0
        done = 0
        for application in applications:
            latest = status_by_app.get(application.id)
            if latest == "completed":
                completed += 1
            elif latest == "failed":
                failed += 1
            elif latest == "processing":
                processing += 1
            elif latest == "pending":
                pending += 1
            # Terminal for progress: scored, failed, or can never be scored (no CV).
            if latest in {"completed", "failed"} or not application.resume_storage_key:
                done += 1

        return {
            "job_id": job_id,
            "total": total,
            "done": done,
            "remaining": max(0, total - done),
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "processing": processing,
        }


@ranking_router.post("/{job_id}/applications/batch", status_code=201)
async def import_job_resumes(
    job_id: int,
    resume_files: list[UploadFile] = File(...),
    actor: User = Depends(require_roles("hiring_manager")),
):
    """Import a batch of CVs for screening and ranking; each file succeeds or fails on its own."""
    if not resume_files:
        raise HTTPException(status_code=422, detail="Choose at least one CV")
    if len(resume_files) > MAX_FILES_PER_REQUEST:
        raise HTTPException(status_code=413, detail=f"Send at most {MAX_FILES_PER_REQUEST} CVs per request")
    with SessionLocal() as session:
        job = session.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.status != "approved":
            raise HTTPException(status_code=409, detail="Approve the job before importing CVs")
    results = []
    for upload in resume_files:
        content = await upload.read(MAX_RESUME_BYTES + 1)
        results.append(import_resume_file(job_id, upload.filename, content, actor.id))
    return {
        "job_id": job_id,
        "queued": sum(1 for item in results if item["status"] == "queued"),
        "duplicates": sum(1 for item in results if item["status"] == "duplicate"),
        "rejected": sum(1 for item in results if item["status"] == "rejected"),
        "accounts_created": sum(1 for item in results if item.get("account_created")),
        "no_email": sum(1 for item in results if item["status"] == "queued" and not item.get("email_found")),
        "results": results,
    }


@ranking_router.post("/{job_id}/finalize-selection")
def finalize_job_selection(
    job_id: int,
    request: FinalizeJobSelection,
    actor: User = Depends(require_roles("hiring_manager")),
):
    """Record the manager's final choice and notify every applicant in one transaction."""
    with SessionLocal() as session:
        job = session.scalar(select(Job).where(Job.id == job_id).with_for_update())
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.status != "approved":
            raise HTTPException(status_code=409, detail="This job is not open for final selection")

        applicants = session.execute(
            select(Application, User)
            .join(User, User.id == Application.candidate_id)
            .where(Application.job_id == job_id, Application.status != "withdrawn")
            .order_by(Application.created_at, Application.id)
        ).all()
        if not applicants:
            raise HTTPException(status_code=409, detail="There are no applicants to finalize")
        if not any(application.id == request.application_id for application, _candidate in applicants):
            raise HTTPException(status_code=404, detail="Selected application does not belong to this job")

        changed = 0
        for application, candidate in applicants:
            next_status = "selected" if application.id == request.application_id else "not selected"
            previous_status = application.status
            if previous_status == next_status:
                continue
            application.status = next_status
            audit = AuditLog(
                actor_user_id=actor.id,
                action="finalize_job_selection",
                target_type="application",
                target_id=str(application.id),
                before_values={"status": previous_status},
                after_values={"status": next_status, "job_id": job_id},
                reason=request.reason,
            )
            session.add(audit)
            session.flush()
            queue_status_email(
                session,
                application,
                application.candidate_email or candidate.email,
                next_status,
                event_key=f"final-selection:{audit.id}",
            )
            changed += 1

        job.status = "filled"
        session.commit()
        return {
            "job_id": job_id,
            "status": "filled",
            "selected_application_id": request.application_id,
            "applicant_count": len(applicants),
            "outcome_emails_queued": changed,
        }


@ranking_router.get("/{job_id}/ranking")
def rank_job_applications(
    job_id: int,
    _actor: User = Depends(require_roles("hiring_manager")),
):
    with SessionLocal() as session:
        if session.get(Job, job_id) is None:
            raise HTTPException(status_code=404, detail="Job not found")
    result = application_ranking_graph.invoke({"job_id": job_id})
    return {
        "job_id": job_id,
        "job_title": result.get("job_title", ""),
        "applications": result.get("applications", []),
    }


@ranking_router.get("/{job_id}/assessment-comparison")
def compare_job_assessments(
    job_id: int,
    _actor: User = Depends(require_roles("hiring_manager")),
):
    with SessionLocal() as session:
        job = session.get(Job, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        applications = session.scalars(
            select(Application)
            .where(Application.job_id == job_id, Application.status != "withdrawn")
            .order_by(Application.created_at)
        ).all()
        candidates = []
        for application in applications:
            score = session.scalar(select(ScreeningScore).where(
                ScreeningScore.application_id == application.id, ScreeningScore.status == "completed"
            ).order_by(ScreeningScore.created_at.desc(), ScreeningScore.id.desc()).limit(1))
            interview = session.scalar(select(Interview).where(Interview.application_id == application.id).limit(1))
            analysis = session.scalar(select(InterviewEvaluation).where(
                InterviewEvaluation.interview_id == interview.id if interview else False,
                InterviewEvaluation.evaluation_type == "f5_analysis",
            ).order_by(InterviewEvaluation.created_at.desc()).limit(1)) if interview else None
            extended = session.scalar(select(InterviewEvaluation).where(
                InterviewEvaluation.interview_id == interview.id if interview else False,
                InterviewEvaluation.evaluation_type == "f8_f9_f10",
            ).order_by(InterviewEvaluation.created_at.desc()).limit(1)) if interview else None
            answers = (analysis.payload or {}).get("answers", []) if analysis else []
            average = lambda key: round(sum(item[key] for item in answers) / len(answers), 2) if answers else None
            candidates.append({
                "application_id": application.id, "candidate_name": application.candidate_name or "Candidate",
                "cv_score": score.total_score if score else None,
                "cv_requirements": (score.breakdown or {}).get("requirements", []) if score else [],
                "interview_component_averages": {key: average(key) for key in ("relevance", "accuracy", "completeness", "articulation")},
                "interview_evidence": answers,
                "evidence_gaps": (analysis.payload or {}).get("never_explored_requirements", []) if analysis else [],
                "f9_weighted_total_out_of_100": (extended.payload or {}).get("f9_weighted_total_out_of_100") if extended else None,
                "f8_claim_verification": (extended.payload or {}).get("f8_claim_verification", []) if extended else [],
                "f10_quality": (extended.payload or {}).get("f10_quality") if extended else None,
            })
        return {"job_id": job.id, "job_title": job.title, "candidates": candidates,
                "human_review_required": True}


@manager_router.get("/{application_id}/assessment")
def get_consolidated_assessment(
    application_id: int,
    _actor: User = Depends(require_roles("hiring_manager")),
):
    assessment = build_consolidated_assessment(application_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return assessment
