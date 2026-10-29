import os
import smtplib
import ssl
from email.message import EmailMessage


def send_application_confirmation(recipient: str, job_title: str, application_id: int) -> bool:
    host = os.getenv("SMTP_HOST", "").strip()
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM_EMAIL", "").strip()
    if not all((host, username, password, sender)):
        return False

    port = int(os.getenv("SMTP_PORT", "587"))
    message = EmailMessage()
    message["Subject"] = f"Application received: {job_title}"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        f"We received your application for {job_title}. "
        f"Your reference number is {application_id}. "
        "Your resume and application details are stored securely in RecruitO."
    )

    context = ssl.create_default_context()
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=context, timeout=15) as smtp:
                smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=15) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        return False
    return True


def send_password_reset_email(recipient: str, reset_link: str) -> bool:
    host = os.getenv("SMTP_HOST", "").strip()
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM_EMAIL", "").strip()
    if not all((host, username, password, sender)):
        return False

    port = int(os.getenv("SMTP_PORT", "587"))
    message = EmailMessage()
    message["Subject"] = "Reset your RecruitO password"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "We received a request to reset your RecruitO password.\n\n"
        f"Reset it here (this link expires in 1 hour):\n{reset_link}\n\n"
        "If you did not request this, you can safely ignore this email; your password will not change."
    )

    context = ssl.create_default_context()
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=context, timeout=15) as smtp:
                smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=15) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        return False
    return True


def send_candidate_invite_email(recipient: str, full_name: str, job_title: str, invite_link: str) -> bool:
    """Invite an imported candidate to set a password so they can sign in and join interviews."""
    host = os.getenv("SMTP_HOST", "").strip()
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    sender = os.getenv("SMTP_FROM_EMAIL", "").strip()
    if not all((host, username, password, sender)):
        return False

    port = int(os.getenv("SMTP_PORT", "587"))
    greeting = f"Hello {full_name}," if full_name else "Hello,"
    message = EmailMessage()
    message["Subject"] = f"Your RecruitO candidate account for {job_title}"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        f"{greeting}\n\n"
        f"Your CV has been added to the hiring process for {job_title} on RecruitO.\n\n"
        "Set your password here to activate your account (this link expires in 7 days):\n"
        f"{invite_link}\n\n"
        "Once your password is set you can sign in to track your application and join your "
        "interview when one is scheduled.\n\n"
        "If you did not expect this email, you can safely ignore it."
    )

    context = ssl.create_default_context()
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=context, timeout=15) as smtp:
                smtp.login(username, password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(host, port, timeout=15) as smtp:
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        return False
    return True
