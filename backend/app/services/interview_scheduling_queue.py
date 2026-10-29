"""Notify the hiring manager when a CV score makes a candidate interview-eligible.

A completed latest CV score strictly above the threshold flips the application to
"selected for interview" and emails the hiring manager, who then assigns the
interview date, time, and interviewer manually from the hiring workspace.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from sqlalchemy import exists, select, update

from app.db.session import SessionLocal
from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.interview import Interview
from app.models.job import Job
from app.models.screening_score import ScreeningScore
from app.models.user import User


logger = logging.getLogger(__name__)
INTERVIEW_SCORE_THRESHOLD = 65.0

# Applications that have reached a final or interview state are never (re)notified.
_FINALIZED_STATUSES = {
    "selected", "not selected", "rejected", "withdrawn",
    "decision made", "decision available", "interview scheduled",
    "interview completed",
}


def _manager_recipient(session, job: Job) -> str | None:
    if job.created_by_id is not None:
        manager = session.get(User, job.created_by_id)
        if manager is not None and manager.role == "hiring_manager" and manager.is_active and manager.email:
            return manager.email
    fallback = os.getenv("HIRING_MANAGER_EMAIL", "").strip()
    return fallback or None


def _notify_manager(application_id: int) -> None:
    from app.services.notifications import queue_email

    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        row = session.execute(
            select(Application, Job, User)
            .join(Job, Job.id == Application.job_id)
            .join(User, User.id == Application.candidate_id)
            .where(Application.id == application_id)
            .with_for_update(of=Application)
        ).first()
        if row is None:
            return
        application, job, candidate = row
        if application.scheduling_status != "pending":
            return

        if job.status != "approved" or application.status in _FINALIZED_STATUSES:
            application.scheduling_status = "cancelled"
            application.scheduling_error_code = "JOB_CLOSED_OR_APPLICATION_FINALIZED"
            session.commit()
            return

        if session.scalar(select(Interview.id).where(Interview.application_id == application.id)):
            application.scheduling_status = "scheduled"
            application.scheduling_error_code = None
            session.commit()
            return

        latest_score = session.scalar(
            select(ScreeningScore)
            .where(
                ScreeningScore.application_id == application.id,
                ScreeningScore.status == "completed",
            )
            .order_by(ScreeningScore.created_at.desc(), ScreeningScore.id.desc())
            .limit(1)
        )
        if latest_score is None or latest_score.total_score is None:
            application.scheduling_status = "not_queued"
            application.scheduling_error_code = None
            session.commit()
            return
        if latest_score.total_score <= INTERVIEW_SCORE_THRESHOLD:
            application.scheduling_status = "not_eligible"
            application.scheduling_error_code = None
            session.commit()
            return

        recipient = _manager_recipient(session, job)
        if recipient is None:
            application.scheduling_status = "blocked"
            application.scheduling_error_code = "NO_HIRING_MANAGER_RECIPIENT"
            session.commit()
            return

        if application.status in {"submitted", "under review"}:
            application.status = "selected for interview"
        application.scheduling_status = "manager_notified"
        application.scheduling_processing_at = None
        application.scheduling_next_attempt_at = None
        application.scheduling_error_code = None

        public_base = os.getenv("PUBLIC_BASE_URL", "http://localhost:5500").strip().rstrip("/")
        workspace_url = f"{public_base}/manager-applications.html#manager-application-{application.id}"
        candidate_name = application.candidate_name or candidate.full_name or "A candidate"
        queue_email(
            session,
            application_id=application.id,
            recipient=recipient,
            status_key=f"manager-interview-eligible:{application.id}:{latest_score.id}"[:80],
            subject=f"Interview candidate ready to schedule: {job.title}",
            body=(
                f"{candidate_name}'s CV for {job.title} scored "
                f"{latest_score.total_score:.0f}/100, above the {INTERVIEW_SCORE_THRESHOLD:.0f}/100 "
                "interview threshold.\n\n"
                "Sign in to RecruitO to assign an interview date, time, and interviewer:\n"
                f"{workspace_url}\n\n"
                "The hiring manager still makes the final decision; a high score is not an automatic selection."
            ),
        )
        session.add(AuditLog(
            actor_user_id=job.created_by_id,
            action="notify_manager_interview_eligible",
            target_type="application",
            target_id=str(application.id),
            before_values={"scheduling_status": "pending"},
            after_values={
                "scheduling_status": "manager_notified",
                "score_id": latest_score.id,
                "total_score": latest_score.total_score,
            },
            reason="RecruitO emailed the hiring manager to schedule an interview after the CV score exceeded 65/100.",
        ))
        session.commit()


def dispatch_pending_interview_scheduling(limit: int = 10) -> int:
    """Queue newly eligible applications, then email the manager for each."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        latest_score_id = (
            select(ScreeningScore.id)
            .where(ScreeningScore.application_id == Application.id)
            .order_by(ScreeningScore.created_at.desc(), ScreeningScore.id.desc())
            .limit(1)
            .scalar_subquery()
        )
        session.execute(
            update(Application)
            .where(
                Application.scheduling_status == "not_queued",
                Application.candidate_removed_at.is_(None),
                Application.status.notin_(_FINALIZED_STATUSES),
                exists(select(ScreeningScore.id).where(
                    ScreeningScore.id == latest_score_id,
                    ScreeningScore.status == "completed",
                    ScreeningScore.total_score > INTERVIEW_SCORE_THRESHOLD,
                )),
                exists(select(Job.id).where(Job.id == Application.job_id, Job.status == "approved")),
                ~exists(select(Interview.id).where(Interview.application_id == Application.id)),
            )
            .values(scheduling_status="pending", scheduling_next_attempt_at=now, scheduling_error_code=None)
        )
        session.commit()

    with SessionLocal() as session:
        application_ids = session.scalars(
            select(Application.id)
            .where(Application.scheduling_status == "pending")
            .order_by(Application.created_at.asc())
            .limit(limit)
        ).all()

    processed = 0
    for application_id in application_ids:
        try:
            _notify_manager(application_id)
        except Exception:
            logger.exception("Manager interview-eligibility notification failed for application %s", application_id)
        else:
            processed += 1
    return processed
