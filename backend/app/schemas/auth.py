from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CandidateRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    phone_number: str = Field(min_length=5, max_length=30)

    @field_validator("full_name", "phone_number")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value

    @field_validator("phone_number")
    @classmethod
    def require_phone_length(cls, value: str) -> str:
        if len(value) < 5:
            raise ValueError("Phone number must contain at least 5 characters")
        return value


class ManagerProfileUpdateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10, max_length=512)
    new_password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: Literal["hiring_manager", "candidate", "interviewer"]
    is_active: bool


class CandidateProfileResponse(BaseModel):
    full_name: str
    email: EmailStr
    phone_number: str | None = None
    education_qualification: str | None = None
    institution_name: str | None = None
    department: str | None = None
    graduation_year: int | None = None


class CandidateProfileUpdateRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    phone_number: str | None = Field(default=None, max_length=30)
    education_qualification: str | None = Field(default=None, max_length=255)
    institution_name: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    graduation_year: int | None = Field(default=None, ge=1950, le=2100)

    @field_validator("full_name")
    @classmethod
    def trim_candidate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Full name cannot be blank")
        return value

    @field_validator(
        "phone_number",
        "education_qualification",
        "institution_name",
        "department",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("phone_number")
    @classmethod
    def require_phone_length(cls, value: str | None) -> str | None:
        if value is not None and len(value) < 5:
            raise ValueError("Phone number must contain at least 5 characters")
        return value


class InterviewerProfileUpdateRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    institute: str | None = Field(default=None, max_length=255)
    experience_years: int | None = Field(default=None, ge=0, le=80)
    experience_summary: str | None = Field(default=None, max_length=2000)
    education: str | None = Field(default=None, max_length=1000)

    @field_validator("full_name")
    @classmethod
    def trim_interviewer_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Full name cannot be blank")
        return value


class InterviewerProfileResponse(BaseModel):
    full_name: str
    email: EmailStr
    institute: str | None = None
    experience_years: int | None = None
    experience_summary: str | None = None
    education: str | None = None
    photo_url: str | None = None


class StaffCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=12, max_length=128)
    role: Literal["hiring_manager", "interviewer"]
    reason: str = Field(min_length=10, max_length=1000)

    @field_validator("full_name", "reason")
    @classmethod
    def strip_full_name(cls, value: str) -> str:
        value = value.strip()
        if not value or ("reason" in cls.model_fields and len(value) < 10):
            raise ValueError("Value cannot be blank; reason must contain at least 10 characters")
        return value


class MessageResponse(BaseModel):
    message: str
