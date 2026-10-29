"""Resume upload validation and hiring-manager batch CV import (F1, N1).

Each imported CV is read for the candidate's name, email and phone (via Gemini,
with a regex email fallback). When a contactable email is found, RecruitO
creates an active candidate account, emails the person a set-password invite so
they can sign in and join interviews, and routes the application through the
normal scheduling pipeline (so a high CV score notifies the hiring manager just
like a direct applicant). When no email can be read, the CV is still scored and
ranked, but it belongs to an inactive, no-login record on the reserved
``.invalid`` domain and receives no email.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import secrets
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.job import Job
from app.models.password_reset import PasswordResetToken
from app.models.screening_score import ScreeningScore
from app.models.user import CandidateProfile, User
from app.services.email_notifications import send_candidate_invite_email
from app.services.screening import digest, extract_resume_text
from app.services.screening_queue import enqueue_application_screening, requirement_data_for_job
from app.services.security import hash_password


logger = logging.getLogger(__name__)
UPLOAD_DIR = Path(os.getenv("CANDIDATE_UPLOAD_DIR", "/data/candidate-resumes"))
MAX_RESUME_BYTES = 10 * 1024 * 1024
# The manager may import any number of CVs; the frontend sends them in small
# chunks and this is the safety cap on a single request. There is no overall
# limit on how many CVs a job can have.
MAX_FILES_PER_REQUEST = 10
IMPORTED_EMAIL_DOMAIN = "imported.recruito.invalid"
MANUAL_SCHEDULING_STATUS = "manual"


class ResumeUploadError(ValueError):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def validate_resume_upload(filename: str | None, content: bytes) -> tuple[str, str]:
    """Check type, size and file signature; return the safe display name and extension."""
    original_name = Path(filename or "resume").name
    extension = Path(original_name).suffix.lower()
    if extension not in {".pdf", ".docx"}:
        raise ResumeUploadError(422, "Upload a PDF or DOCX resume")
    if len(content) > MAX_RESUME_BYTES:
        raise ResumeUploadError(413, "Resume must be 10 MB or smaller")
    valid_pdf = extension == ".pdf" and content.startswith(b"%PDF-")
    valid_docx = False
    if extension == ".docx" and content.startswith(b"PK"):
        try:
            with zipfile.ZipFile(BytesIO(content)) as archive:
                valid_docx = "word/document.xml" in archive.namelist()
        except zipfile.BadZipFile:
            valid_docx = False
    if not (valid_pdf or valid_docx):
        raise ResumeUploadError(422, "The uploaded file is not a valid PDF or DOCX resume")
    return original_name[:255] or f"resume{extension}", extension


def is_imported_candidate_email(email: str | None) -> bool:
    return bool(email) and email.lower().endswith("@" + IMPORTED_EMAIL_DOMAIN)


def _display_name(file_name: str) -> str:
    stem = Path(file_name).stem
    name = re.sub(r"[\s_.\-]+", " ", stem).strip()
    return (name.title() if name else "Imported candidate")[:255]


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def _parse_json_object(text: str) -> dict:
    if not text:
        return {}
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned).rstrip("`").strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        return {}
    try:
        data = json.loads(cleaned[start : end + 1])
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, ValueError):
        return {}


def extract_contact_details(resume_text: str) -> dict:
    """Pull the candidate's name, email and phone from CV text (Gemini + regex fallback)."""
    result: dict[str, str | None] = {"full_name": None, "email": None, "phone": None}
    if not resume_text:
        return result

    regex_email = EMAIL_RE.search(resume_text)
    if regex_email:
        result["email"] = regex_email.group(0)

    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            from google import genai

            prompt = (
                "Extract the candidate's contact details from this CV text. "
                "Return ONLY a JSON object with keys full_name, email, phone. "
                "Use null for any field you cannot find. Do not invent values.\n\n"
                f"CV text:\n{resume_text[:12000]}"
            )
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=os.getenv("CHAT_MODEL", "gemini-3.1-flash-lite"),
                contents=prompt,
            )
            data = _parse_json_object(response.text or "")
            for key in ("full_name", "email", "phone"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    result[key] = value.strip()
        except Exception:  # noqa: BLE001 - extraction is best-effort
            logger.exception("Contact extraction via Gemini failed")

    # Normalise the email: trust the model only if it is a well-formed address,
    # otherwise fall back to the first address the regex found in the raw text.
    email = (result["email"] or "").strip()
    if email and not EMAIL_RE.fullmatch(email):
        found = EMAIL_RE.search(email) or EMAIL_RE.search(resume_text)
        email = found.group(0) if found else ""
    result["email"] = email.lower()[:255] or None
    if result["full_name"]:
        result["full_name"] = result["full_name"][:255]
    if result["phone"]:
        result["phone"] = result["phone"][:30]
    return result


def _invite_link(raw_token: str) -> str:
    base = os.getenv("PUBLIC_BASE_URL", "http://localhost:5500").strip().rstrip("/")
    return f"{base}/reset-password.html?token={raw_token}"


def import_resume_file(job_id: int, file_name: str | None, content: bytes, actor_user_id: int | None) -> dict:
    """Create one imported application and queue its screening.

    Each file commits on its own, so one unreadable or duplicate CV never
    aborts the rest of the batch.
    """
    try:
        safe_name, extension = validate_resume_upload(file_name, content)
    except ResumeUploadError as exc:
        return {"file_name": Path(file_name or "resume").name, "status": "rejected", "error": exc.detail}

    cv_hash = digest(content)
    storage_key = f"{uuid.uuid4().hex}{extension}"
    stored_path = UPLOAD_DIR / storage_key

    # Read the CV text once to pull the candidate's contact details.
    try:
        resume_text = extract_resume_text(content, safe_name)
    except Exception:  # noqa: BLE001 - scoring still runs on the raw bytes
        resume_text = ""
    contact = extract_contact_details(resume_text)
    extracted_name = contact["full_name"] or _display_name(safe_name)
    email = contact["email"]
    phone = contact["phone"]

    with SessionLocal() as session:
        job = session.get(Job, job_id)
        if job is None or job.status != "approved":
            return {"file_name": safe_name, "status": "rejected", "error": "Job is not open for applications"}
        job_title = job.title

        duplicate_id = session.scalar(
            select(Application.id)
            .join(ScreeningScore, ScreeningScore.application_id == Application.id)
            .where(Application.job_id == job_id, ScreeningScore.cv_hash == cv_hash)
            .limit(1)
        )
        if duplicate_id is not None:
            return {"file_name": safe_name, "status": "duplicate", "application_id": duplicate_id,
                    "error": "This CV was already imported for this job"}

        # If the email belongs to an existing non-candidate account we cannot reuse
        # it (and must not collide with the unique email), so treat it as no-email.
        existing = None
        if email:
            existing = session.scalar(select(User).where(func.lower(User.email) == email))
            if existing is not None and existing.role != "candidate":
                email = None
                existing = None

        notify_enabled = False

        if email and existing is not None:
            # Reuse the real candidate's account; link a fresh application to it.
            dup_app = session.scalar(
                select(Application.id).where(
                    Application.candidate_id == existing.id, Application.job_id == job_id
                )
            )
            if dup_app is not None:
                return {"file_name": safe_name, "status": "duplicate", "application_id": dup_app,
                        "error": "This candidate already has an application for this job"}
            candidate = existing
            profile = candidate.candidate_profile
            if profile is None:
                profile = CandidateProfile(user_id=candidate.id, certificate_full_name=extracted_name)
                candidate.candidate_profile = profile
            profile.resume_storage_key = storage_key
            profile.resume_file_name = safe_name
            if not profile.contact_email:
                profile.contact_email = candidate.email
            if phone and not profile.phone_number:
                profile.phone_number = phone
            notify_enabled = True
        elif email:
            # New, contactable candidate: active account that still needs a password.
            # The set-password invite is sent when the manager schedules the interview,
            # not at import time, so only candidates who are actually interviewed are emailed.
            candidate = User(
                email=email,
                password_hash=hash_password(secrets.token_urlsafe(32)),
                role="candidate",
                full_name=extracted_name,
                is_active=True,
                password_pending=True,
            )
            candidate.candidate_profile = CandidateProfile(
                certificate_full_name=extracted_name,
                contact_email=email,
                phone_number=phone,
                resume_storage_key=storage_key,
                resume_file_name=safe_name,
            )
            session.add(candidate)
            session.flush()
            notify_enabled = True
        else:
            # No contactable email: keep an inactive, no-login record (still scored).
            candidate = User(
                email=f"{uuid.uuid4().hex}@{IMPORTED_EMAIL_DOMAIN}",
                password_hash=hash_password(secrets.token_urlsafe(32)),
                role="candidate",
                full_name=extracted_name,
                is_active=False,
            )
            candidate.candidate_profile = CandidateProfile(
                certificate_full_name=extracted_name,
                phone_number=phone,
                resume_storage_key=storage_key,
                resume_file_name=safe_name,
            )
            session.add(candidate)
            session.flush()

        application = Application(
            candidate_id=candidate.id,
            job_id=job_id,
            candidate_name=extracted_name,
            candidate_email=email,
            candidate_phone=phone,
            resume_storage_key=storage_key,
            resume_file_name=safe_name,
            scheduling_status=("not_queued" if notify_enabled else MANUAL_SCHEDULING_STATUS),
        )
        session.add(application)
        session.flush()
        score = enqueue_application_screening(
            session,
            application,
            content,
            requirement_data_for_job(session, job_id),
            job.jd_text or "",
        )
        session.add(AuditLog(
            actor_user_id=actor_user_id,
            action="import_candidate_resume",
            target_type="application",
            target_id=str(application.id),
            before_values=None,
            after_values={
                "job_id": job_id,
                "resume_file_name": safe_name,
                "email_found": bool(email),
                "account_created": bool(email and existing is None),
                "reused_account": bool(email and existing is not None),
            },
            reason="Hiring manager batch CV import for screening and ranking.",
        ))
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        stored_path.write_bytes(content)
        try:
            session.commit()
        except Exception:
            session.rollback()
            stored_path.unlink(missing_ok=True)
            logger.exception("Could not import CV for job %s", job_id)
            return {"file_name": safe_name, "status": "rejected", "error": "The CV could not be saved"}
        application_id = application.id
        score_status = score.status
        account_created = bool(email and existing is None)

    return {
        "file_name": safe_name,
        "status": "queued",
        "application_id": application_id,
        "score_status": score_status,
        "email_found": bool(email),
        "account_created": account_created,
    }
