import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from io import BytesIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import FileResponse
from sqlalchemy import delete, func, select

from app.db.session import SessionLocal
from app.dependencies import require_roles
from app.models.user import CandidateProfile, InterviewerProfile, User
from app.models.audit_log import AuditLog
from app.models.password_reset import PasswordResetToken
from app.models.screening_score import BiometricEnrollment
from app.schemas.auth import (
    CandidateProfileResponse,
    CandidateProfileUpdateRequest,
    CandidateRegisterRequest,
    ForgotPasswordRequest,
    ManagerProfileUpdateRequest,
    MessageResponse,
    ResetPasswordRequest,
    UserResponse,
    InterviewerProfileResponse,
    InterviewerProfileUpdateRequest,
    StaffCreateRequest,
)
from app.services.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.services.email_notifications import send_password_reset_email
from app.services.face_biometrics import create_embedding


router = APIRouter(prefix="/auth", tags=["auth"])
candidate_profile_router = APIRouter(prefix="/me", tags=["candidate profile"])
interviewer_profile_router = APIRouter(prefix="/me", tags=["interviewer profile"])
staff_router = APIRouter(prefix="/admin/staff", tags=["staff administration"])
STAFF_PHOTO_DIR = Path(os.getenv("STAFF_PHOTO_DIR", "/data/staff-photos"))
MAX_STAFF_PHOTO_BYTES = 5 * 1024 * 1024
MAX_BIOMETRIC_IMAGE_BYTES = 2 * 1024 * 1024


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        path="/",
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        httponly=True,
        samesite="lax",
    )
    return MessageResponse(message="Signed out successfully")


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_candidate(request: CandidateRegisterRequest):
    with SessionLocal() as session:
        existing_user = session.scalar(
            select(User).where(User.email == request.email)
        )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered",
            )

        user = User(
            email=str(request.email),
            password_hash=hash_password(request.password),
            role="candidate",
            full_name=request.full_name.strip(),
            is_active=True,
            candidate_profile=CandidateProfile(
                contact_email=str(request.email),
                phone_number=request.phone_number.strip(),
                certificate_full_name=request.full_name.strip(),
            ),
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        return user


@candidate_profile_router.get(
    "/profile",
    response_model=CandidateProfileResponse,
)
def get_candidate_profile(
    current_user: User = Depends(require_roles("candidate")),
):
    with SessionLocal() as session:
        user = session.scalar(
            select(User).where(User.id == current_user.id)
        )
        if user is None or user.candidate_profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate profile not found",
            )

        profile = user.candidate_profile
        return CandidateProfileResponse(
            full_name=profile.certificate_full_name or user.full_name,
            email=profile.contact_email or user.email,
            phone_number=profile.phone_number,
            education_qualification=profile.education_qualification,
            institution_name=profile.institution_name,
            department=profile.department,
            graduation_year=profile.graduation_year,
        )


@candidate_profile_router.put(
    "/profile",
    response_model=CandidateProfileResponse,
)
def update_candidate_profile(
    request: CandidateProfileUpdateRequest,
    current_user: User = Depends(require_roles("candidate")),
):
    with SessionLocal() as session:
        user = session.scalar(
            select(User).where(User.id == current_user.id)
        )
        if user is None or user.candidate_profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate profile not found",
            )

        profile = user.candidate_profile
        profile.certificate_full_name = request.full_name
        profile.phone_number = request.phone_number
        profile.education_qualification = request.education_qualification
        profile.institution_name = request.institution_name
        profile.department = request.department
        profile.graduation_year = request.graduation_year
        session.commit()
        session.refresh(profile)

        return CandidateProfileResponse(
            full_name=profile.certificate_full_name or user.full_name,
            email=profile.contact_email or user.email,
            phone_number=profile.phone_number,
            education_qualification=profile.education_qualification,
            institution_name=profile.institution_name,
            department=profile.department,
            graduation_year=profile.graduation_year,
        )


@candidate_profile_router.get("/biometric-enrollment")
def biometric_enrollment_status(current_user: User = Depends(require_roles("candidate"))):
    with SessionLocal() as session:
        row = session.get(BiometricEnrollment, current_user.id)
        active = bool(row and row.revoked_at is None and row.retention_until > datetime.now(timezone.utc))
        return {"enrolled": active, "consented_at": row.consented_at if active else None,
                "retention_until": row.retention_until if active else None}


@candidate_profile_router.post("/biometric-enrollment", status_code=201)
async def enroll_biometric_profile(
    consent: bool = Form(...),
    reference_photo: UploadFile = File(...),
    current_user: User = Depends(require_roles("candidate")),
):
    if consent is not True:
        raise HTTPException(status_code=422, detail="Explicit biometric consent is required")
    raw = await reference_photo.read(MAX_BIOMETRIC_IMAGE_BYTES + 1)
    try:
        embedding = create_embedding(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Biometric matching is not configured") from exc
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        row = session.get(BiometricEnrollment, current_user.id)
        if row is None:
            row = BiometricEnrollment(candidate_id=current_user.id, embedding=embedding,
                consented_at=now, retention_until=now + timedelta(days=30),
                revoked_at=None, model_name="OpenCV YuNet + SFace")
            session.add(row)
        else:
            row.embedding = embedding
            row.consented_at = now
            row.retention_until = now + timedelta(days=30)
            row.revoked_at = None
            row.model_name = "OpenCV YuNet + SFace"
        session.commit()
        return {"enrolled": True, "consented_at": now, "retention_until": row.retention_until,
                "raw_photo_stored": False}


@candidate_profile_router.delete("/biometric-enrollment")
def revoke_biometric_consent(current_user: User = Depends(require_roles("candidate"))):
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        row = session.get(BiometricEnrollment, current_user.id)
        if row and row.revoked_at is None:
            row.embedding = []
            row.revoked_at = now
            session.commit()
    return {"enrolled": False, "message": "Biometric consent revoked and the stored face representation removed."}


@router.get("/profile", response_model=UserResponse)
def get_manager_profile(
    current_user: User = Depends(require_roles("hiring_manager")),
):
    return current_user


@router.put("/profile", response_model=UserResponse)
def update_manager_profile(
    request: ManagerProfileUpdateRequest,
    current_user: User = Depends(require_roles("hiring_manager")),
):
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.id == current_user.id))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found",
            )

        existing_email = session.scalar(
            select(User).where(
                User.email == str(request.email),
                User.id != current_user.id,
            )
        )
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already in use",
            )

        user.email = str(request.email)
        user.full_name = request.full_name.strip()
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user


@interviewer_profile_router.get("/interviewer-profile", response_model=InterviewerProfileResponse)
def get_interviewer_profile(current_user: User = Depends(require_roles("interviewer"))):
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.id == current_user.id))
        profile = user.interviewer_profile if user else None
        if user is None or profile is None:
            raise HTTPException(status_code=404, detail="Interviewer profile not found")
        return InterviewerProfileResponse(
            full_name=user.full_name, email=user.email, institute=profile.institute,
            experience_years=profile.experience_years, experience_summary=profile.experience_summary,
            education=profile.education,
            photo_url=(f"/me/interviewer-profile/photo" if profile.photo_storage_key else None),
        )


@interviewer_profile_router.put("/interviewer-profile", response_model=InterviewerProfileResponse)
def update_interviewer_profile(
    request: InterviewerProfileUpdateRequest,
    current_user: User = Depends(require_roles("interviewer")),
):
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.id == current_user.id))
        if user is None:
            raise HTTPException(status_code=404, detail="Account not found")
        email_owner = session.scalar(select(User).where(User.email == str(request.email), User.id != user.id))
        if email_owner:
            raise HTTPException(status_code=409, detail="Email is already in use")
        user.full_name = request.full_name.strip()
        user.email = str(request.email)
        profile = user.interviewer_profile
        if profile is None:
            profile = InterviewerProfile(user_id=user.id)
            session.add(profile)
        values = request.model_dump(exclude={"full_name", "email"})
        for field, value in values.items():
            setattr(profile, field, value.strip() if isinstance(value, str) else value)
        session.commit()
        session.refresh(profile)
        return InterviewerProfileResponse(
            full_name=user.full_name, email=user.email, institute=profile.institute,
            experience_years=profile.experience_years, experience_summary=profile.experience_summary,
            education=profile.education,
            photo_url=(f"/me/interviewer-profile/photo" if profile.photo_storage_key else None),
        )


@interviewer_profile_router.post("/interviewer-profile/photo", response_model=InterviewerProfileResponse)
async def upload_interviewer_photo(
    photo: UploadFile = File(...),
    current_user: User = Depends(require_roles("interviewer")),
):
    raw = await photo.read(MAX_STAFF_PHOTO_BYTES + 1)
    if len(raw) > MAX_STAFF_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="Profile photo must be 5 MB or smaller")
    try:
        from PIL import Image
        image = Image.open(BytesIO(raw))
        image.verify()
        image = Image.open(BytesIO(raw)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Upload a valid JPEG, PNG, or WebP image") from exc
    key = f"{uuid.uuid4().hex}.jpg"
    STAFF_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    image.save(STAFF_PHOTO_DIR / key, format="JPEG", quality=90, optimize=True)
    with SessionLocal() as session:
        profile = session.get(InterviewerProfile, current_user.id)
        if profile is None:
            profile = InterviewerProfile(user_id=current_user.id)
            session.add(profile)
        old_key = profile.photo_storage_key
        profile.photo_storage_key = key
        session.commit()
    if old_key:
        (STAFF_PHOTO_DIR / old_key).unlink(missing_ok=True)
    return get_interviewer_profile(current_user)


@interviewer_profile_router.get("/interviewer-profile/photo")
def get_interviewer_photo(current_user: User = Depends(require_roles("interviewer"))):
    with SessionLocal() as session:
        profile = session.get(InterviewerProfile, current_user.id)
        key = profile.photo_storage_key if profile else None
    if not key:
        raise HTTPException(status_code=404, detail="Profile photo not found")
    path = STAFF_PHOTO_DIR / key
    if not path.is_file() or path.parent.resolve() != STAFF_PHOTO_DIR.resolve():
        raise HTTPException(status_code=404, detail="Profile photo not found")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=300"})


@staff_router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_staff_account(
    request: StaffCreateRequest,
    manager: User = Depends(require_roles("hiring_manager")),
):
    with SessionLocal() as session:
        if session.scalar(select(User).where(User.email == str(request.email))):
            raise HTTPException(status_code=409, detail="Email is already registered")
        user = User(
            email=str(request.email), full_name=request.full_name,
            password_hash=hash_password(request.password), role=request.role,
            is_active=True,
        )
        if request.role == "interviewer":
            user.interviewer_profile = InterviewerProfile()
        session.add(user)
        session.flush()
        session.add(AuditLog(
            actor_user_id=manager.id, action="create_staff_account", target_type="user",
            target_id=str(user.id), before_values=None,
            after_values={"role": user.role, "email": user.email}, reason=request.reason,
        ))
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user


@staff_router.get("", response_model=list[UserResponse])
def list_interviewers(_manager: User = Depends(require_roles("hiring_manager"))):
    with SessionLocal() as session:
        return session.scalars(
            select(User).where(User.role == "interviewer", User.is_active.is_(True)).order_by(User.full_name)
        ).all()


@staff_router.patch("/{user_id}/deactivate", response_model=MessageResponse)
def deactivate_staff_account(
    user_id: int,
    request: dict,
    manager: User = Depends(require_roles("hiring_manager")),
):
    reason = request.get("reason", "").strip() if isinstance(request, dict) else ""
    if len(reason) < 10 or len(reason) > 1000:
        raise HTTPException(status_code=422, detail="Reason must contain 10 to 1000 characters")
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.id == user_id, User.role.in_(("hiring_manager", "interviewer"))))
        if user is None:
            raise HTTPException(status_code=404, detail="Staff account not found")
        if user.id == manager.id:
            raise HTTPException(status_code=409, detail="You cannot deactivate your own account")
        if not user.is_active:
            return MessageResponse(message="Staff account is already deactivated")
        if user.role == "hiring_manager":
            other_manager = session.scalar(select(User.id).where(User.role == "hiring_manager", User.is_active.is_(True), User.id != user.id).limit(1))
            if other_manager is None:
                raise HTTPException(status_code=409, detail="The last active hiring manager cannot be deactivated")
        session.add(AuditLog(
            actor_user_id=manager.id, action="deactivate_staff_account", target_type="user",
            target_id=str(user.id), before_values={"is_active": True, "role": user.role},
            after_values={"is_active": False}, reason=reason,
        ))
        user.is_active = False
        session.commit()
        return MessageResponse(message="Staff account deactivated")

@router.post("/login", response_model=UserResponse)
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    with SessionLocal() as session:
        user = session.scalar(
            select(User).where(User.email == form_data.username)
        )

        if (
            user is None
            or not verify_password(form_data.password, user.password_hash)
            or not user.is_active
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = create_access_token(user.id, user.role)
        expires_minutes = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        )

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
            samesite="lax",
            max_age=expires_minutes * 60,
            path="/",
        )

        return user


def _reset_link(raw_token: str) -> str:
    base = os.getenv("PUBLIC_BASE_URL", "http://localhost:5500").strip().rstrip("/")
    return f"{base}/reset-password.html?token={raw_token}"


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(request: ForgotPasswordRequest):
    # Always respond the same way so the endpoint never reveals which emails exist.
    generic = MessageResponse(
        message="If an account with that email exists, a password reset link has been sent."
    )
    email = request.email.strip().lower()
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        user = session.scalar(
            select(User).where(func.lower(User.email) == email, User.is_active.is_(True))
        )
        if user is None:
            return generic
        # Invalidate any previous reset tokens for this user, then issue a fresh one.
        session.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
        raw_token = secrets.token_urlsafe(32)
        session.add(PasswordResetToken(
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            user_id=user.id,
            expires_at=now + timedelta(hours=1),
        ))
        session.commit()
        recipient = user.email
    send_password_reset_email(recipient, _reset_link(raw_token))
    return generic


@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, response: Response):
    token_hash = hashlib.sha256(request.token.encode()).hexdigest()
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        row = session.scalar(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        if row is None or row.used_at is not None or row.expires_at <= now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This reset link is invalid or has expired. Request a new one.",
            )
        user = session.get(User, row.user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This reset link is invalid or has expired. Request a new one.",
            )
        user.password_hash = hash_password(request.new_password)
        user.password_pending = False
        row.used_at = now
        session.add(AuditLog(
            actor_user_id=user.id,
            action="password_reset_via_email",
            target_type="user",
            target_id=str(user.id),
            before_values=None,
            after_values={"method": "email_token"},
            reason="User reset their password using an emailed link.",
        ))
        session.commit()
        user_id, user_role = user.id, user.role

    # Sign the user in immediately so they land on their dashboard, not the login page.
    access_token = create_access_token(user_id, user_role)
    expires_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        max_age=expires_minutes * 60,
        path="/",
    )
    return {"message": "Your password has been set. Signing you in…", "role": user_role}
