from __future__ import annotations

import os
import smtplib
import ssl
import logging
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from sqlalchemy import or_, select

from app.db.session import SessionLocal
from app.models.notification import Notification

logger = logging.getLogger(__name__)

PUBLIC_STATUS = {
    "submitted": "Under review",
    "under review": "Under review",
    "selected for interview": "Interview stage",
    "interview stage": "Interview stage",
    "selected": "Selected",
    "not selected": "Not selected",
    "rejected": "Not selected",
    "interview scheduled": "Interview scheduled",
    "interview rescheduled": "Interview scheduled",
    "interview cancelled": "Under review",
    "interview completed": "Awaiting decision",
    "decision made": "Decision available",
    "decision available": "Decision available",
}


def queue_email(
    session,
    *,
    application_id: int,
    recipient: str,
    status_key: str,
    subject: str,
    body: str,
    payload: dict | None = None,
    available_at: datetime | None = None,
) -> None:
    # Batch-imported candidates have reserved .invalid addresses (RFC 2606) and no inbox.
    if not recipient or recipient.strip().lower().endswith(".invalid"):
        return
    existing = session.scalar(
        select(Notification).where(
            Notification.application_id == application_id,
            Notification.status_key == status_key,
        )
    )
    if existing:
        if existing.state in {"cancelled", "failed"}:
            existing.recipient_email = recipient
            existing.subject = subject[:255]
            existing.body = body
            existing.payload = payload
            existing.available_at = available_at
            existing.state = "pending"
            existing.attempts = 0
            existing.last_error = None
            existing.sending_at = None
            existing.sent_at = None
        return
    session.add(Notification(
        application_id=application_id,
        recipient_email=recipient,
        status_key=status_key,
        subject=subject[:255],
        body=body,
        payload=payload,
        state="pending",
        attempts=0,
        available_at=available_at,
    ))


def queue_status_email(session, application, recipient: str, new_internal_status: str, event_key: str | None = None) -> None:
    status_key = new_internal_status.strip().lower().replace("_", " ")
    visible = PUBLIC_STATUS.get(status_key)
    if not visible:
        return
    queue_email(
        session,
        application_id=application.id,
        recipient=recipient,
        status_key=f"candidate-status:{event_key or status_key}"[:80],
        subject="Update on your RecruitO application" if visible == "Not selected" else f"Application update: {visible}",
        body=(
            "Thank you for applying. After reviewing your application, we will not be moving forward with your application for this role. We appreciate the time you put into applying and wish you the best in your search."
            if visible == "Not selected"
            else (
                "Congratulations. The hiring team selected your application for this role. The hiring team will contact you with next steps."
                if visible == "Selected"
                else f"Your application status has been updated to: {visible}."
            )
        ),
    )


def _send(notification: Notification) -> None:
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    if smtp_host:
        host = smtp_host
        port = int(os.getenv("SMTP_PORT", "587"))
        username = os.getenv("SMTP_USERNAME", "").strip()
        sender = os.getenv("SMTP_FROM_EMAIL", "").strip() or username or "RecruitO <no-reply@recruito.local>"
        password = os.getenv("SMTP_PASSWORD", "")
        tls_setting = os.getenv("SMTP_USE_TLS", "").strip().lower()
    else:
        host = os.getenv("APP_MAIL_HOST", "mailpit").strip()
        port = int(os.getenv("APP_MAIL_PORT", "1025"))
        sender = os.getenv("APP_MAIL_SENDER", "RecruitO <no-reply@recruito.local>").strip()
        username = os.getenv("APP_MAIL_USERNAME", "").strip()
        password = os.getenv("APP_MAIL_PASSWORD", "")
        tls_setting = os.getenv("APP_MAIL_USE_TLS", "").strip().lower()
    use_tls = tls_setting == "true" if tls_setting in {"true", "false"} else port in {465, 587}
    message = EmailMessage()
    message["Subject"] = notification.subject
    message["From"] = sender
    message["To"] = notification.recipient_email
    message.set_content(notification.body)
    payload = notification.payload or {}
    ics = payload.get("ics")
    if isinstance(ics, str) and ics:
        message.add_attachment(ics.encode("utf-8"), maintype="text", subtype="calendar", filename="interview.ics", params={"method": "REQUEST", "charset": "UTF-8"})
    context = ssl.create_default_context()
    if port == 465 and use_tls:
        with smtplib.SMTP_SSL(host, port, context=context, timeout=15) as smtp:
            if username and password:
                smtp.login(username, password)
            smtp.send_message(message)
        return
    with smtplib.SMTP(host, port, timeout=15) as smtp:
        if use_tls:
            smtp.starttls(context=context)
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)


def dispatch_pending_notifications(limit: int = 20) -> int:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        stale = session.scalars(select(Notification).where(
            Notification.state == "sending",
            Notification.sending_at < now - timedelta(minutes=10),
        )).all()
        for item in stale:
            item.state = "pending"
            item.sending_at = None
        if stale:
            session.flush()
        notifications = session.scalars(
            select(Notification)
            .where(
                Notification.state == "pending",
                Notification.attempts < 5,
                or_(Notification.available_at.is_(None), Notification.available_at <= now),
            )
            .order_by(Notification.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(limit)
        ).all()
        ids = [item.id for item in notifications]
        for item in notifications:
            item.state = "sending"
            item.sending_at = now
        session.commit()

    sent = 0
    for notification_id in ids:
        with SessionLocal() as session:
            item = session.get(Notification, notification_id)
            if item is None or item.state != "sending":
                continue
            snapshot = Notification(
                application_id=item.application_id,
                recipient_email=item.recipient_email,
                status_key=item.status_key,
                subject=item.subject,
                body=item.body,
                payload=item.payload,
            )
            try:
                _send(snapshot)
                item.state = "sent"
                item.sent_at = datetime.now(timezone.utc)
                item.recipient_email = ""
                item.body = ""
                item.payload = None
                item.last_error = None
                item.sending_at = None
                sent += 1
            except Exception:
                logger.exception("Could not send queued notification %s", notification_id)
                item.attempts += 1
                item.last_error = "Mail transport failed"
                item.state = "failed" if item.attempts >= 5 else "pending"
                item.sending_at = None
                item.available_at = (
                    datetime.now(timezone.utc) + timedelta(seconds=min(30 * (2 ** (item.attempts - 1)), 300))
                    if item.state == "pending"
                    else None
                )
            session.commit()
    return sent
