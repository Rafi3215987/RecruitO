from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CandidateApplicationSubmission(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone_number: str = Field(min_length=5, max_length=30)
    education_qualification: str = Field(min_length=1, max_length=255)
    institution_name: str = Field(min_length=1, max_length=255)
    department: str = Field(min_length=1, max_length=255)
    graduation_year: int | None = Field(default=None, ge=1950, le=2100)

    @field_validator(
        "full_name",
        "phone_number",
        "education_qualification",
        "institution_name",
        "department",
    )
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


class ApplicationSubmittedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    status: str
    created_at: datetime
    confirmation_email_queued: bool = False
    score_status: str = "pending"
    scheduling_status: str = "not_queued"


class CandidateApplicationItem(BaseModel):
    id: int
    interview_id: int | None = None
    job_id: int
    job_title: str
    seniority: str
    applied_at: datetime
    status: str
    interview_scheduled_at: datetime | None = None
    interview_duration_minutes: int | None = None
    interview_scheduling_status: str = "not_queued"
    interview_scheduling_error_code: str | None = None
    join_available: bool = False


class HiringManagerApplicationItem(BaseModel):
    id: int
    interview_id: int | None = None
    job_id: int
    candidate_name: str
    candidate_email: str
    candidate_phone: str | None = None
    education_qualification: str | None = None
    institution_name: str | None = None
    department: str | None = None
    graduation_year: int | None = None
    resume_file_name: str | None = None
    job_title: str
    status: str
    applied_at: datetime
    score_status: str = "not_started"
    total_score: float | None = None
    score_error_code: str | None = None
    interview_scheduled_at: datetime | None = None
    interview_duration_minutes: int | None = None
    interview_ended_at: datetime | None = None
    interview_status: str | None = None
    interviewer_id: int | None = None
    interview_analysis_status: str = "not_started"
    interview_analysis_error_code: str | None = None
    interview_scheduling_status: str = "not_queued"
    interview_scheduling_error_code: str | None = None


class FinalizeJobSelection(BaseModel):
    application_id: int = Field(gt=0)
    reason: str = Field(min_length=10, max_length=1000)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise ValueError("Give a reason with at least 10 non-space characters")
        return value


class ManagerCandidateCorrection(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone_number: str | None = Field(default=None, min_length=5, max_length=30)
    education_qualification: str | None = Field(default=None, max_length=255)
    institution_name: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    graduation_year: int | None = Field(default=None, ge=1950, le=2100)

    @field_validator("reason")
    @classmethod
    def valid_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise ValueError("Give a reason with at least 10 non-space characters")
        return value


class ManagerApplicationStatusChange(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)
    status: str = Field(pattern="^(under review|interview stage|not selected|interview scheduled|awaiting decision|decision available)$")

    @field_validator("reason")
    @classmethod
    def valid_status_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise ValueError("Give a reason with at least 10 non-space characters")
        return value


class ManagerActionReason(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise ValueError("Reason must contain at least 10 non-space characters")
        return value
