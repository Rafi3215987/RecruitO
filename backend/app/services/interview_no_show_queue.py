"""Automatically reject applications when the candidate never joins an interview."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.interview import Interview
from app.models.job import Job
from app.models.user import User
from app.services.notifications import queue_email


JOIN_GRACE = timedelta(minutes=30)
PENDING_INTERVIEW_STATUSES = {"selected for interview", "interview scheduled"}
# Interviews already in progress when this tracking code starts cannot be
# reliably classified because candidate attendance was not previously stored.
TRACKING_ENABLED_AT = datetime.now(timezone.utc)


def dispatch_overdue_interview_no_shows(limit: int = 100) -> int:
    """Mark missed interviews and queue an explanatory candidate email.

    Candidates retain the existing 30-minute post-interview join window. An
    interview is marked as a no-show only after that window closes and only if
    the candidate never established an authenticated interview connection.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - JOIN_GRACE
    updated = 0

    with SessionLocal() as session:
        rows = session.execute(
            select(Interview, Application, Job, User)
            .join(Application, Application.id == Interview.application_id)
            .join(Job, Job.id == Application.job_id)
            .join(User, User.id == Application.candidate_id)
            .where(
                Interview.status == "scheduled",
                Interview.candidate_joined_at.is_(None),
                Interview.scheduled_at <= cutoff,
                Interview.scheduled_at >= TRACKING_ENABLED_AT,
            )
            .order_by(Interview.scheduled_at.asc(), Interview.id.asc())
            .with_for_update(skip_locked=True, of=Interview)
            .limit(limit)
        ).all()

        for interview, application, job, candidate in rows:
            scheduled_at = interview.scheduled_at
            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
            else:
                scheduled_at = scheduled_at.astimezone(timezone.utc)
            join_window_ends = scheduled_at + timedelta(
                minutes=interview.duration_minutes
            ) + JOIN_GRACE
            if join_window_ends > now:
                continue

            interview.status = "no_show"
            interview.ended_at = now

            # Keep an existing hiring decision intact; only reject applications
            # that are still waiting at the interview stage.
            if application.status in PENDING_INTERVIEW_STATUSES:
                previous_status = application.status
                application.status = "not selected"
                session.add(AuditLog(
                    actor_user_id=None,
                    action="automatic_interview_no_show_rejection",
                    target_type="application",
                    target_id=str(application.id),
                    before_values={"status": previous_status},
                    after_values={"status": "not selected", "interview_id": interview.id},
                    reason="The scheduled interview join window ended without an authenticated candidate connection.",
                ))

                recipient = application.candidate_email or candidate.email
                queue_email(
                    session,
                    application_id=application.id,
                    recipient=recipient,
                    status_key=f"candidate-status:interview-no-show:{interview.id}"[:80],
                    subject=f"Interview missed: application update for {job.title}",
                    body=(
                        f"Our records show that you did not join your scheduled interview for {job.title}. "
                        f"The interview was scheduled for {scheduled_at.isoformat()} and its join window has now closed. "
                        "Your application status has been updated to Not selected. If you believe this status is incorrect, "
                        "please contact the hiring team."
                    ),
                )
            updated += 1

        if updated:
            session.commit()

    return updated
