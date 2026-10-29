from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Literal


class InterviewScheduleRequest(BaseModel):
    scheduled_at: datetime
    duration_minutes: int = Field(ge=15, le=240)
    interviewer_id: int

    @field_validator("scheduled_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("scheduled_at must include a timezone")
        return value


class InterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    scheduled_at: datetime
    duration_minutes: int
    status: str
    interviewer_id: int | None = None
    join_available: bool = False


class InterviewerInterviewItem(BaseModel):
    interview_id: int
    application_id: int
    candidate_name: str
    job_title: str
    scheduled_at: datetime
    duration_minutes: int
    status: str
    join_url: str | None = None


class InterviewerApplicationItem(BaseModel):
    application_id: int
    candidate_name: str
    job_title: str
    seniority: str
    status: str
    applied_at: datetime


class ManagerInterviewChange(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)
    scheduled_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=15, le=240)
    interviewer_id: int | None = None
    cancel: bool = False

    @field_validator("scheduled_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("scheduled_at must include a timezone")
        return value


class MockTranscriptSegmentRequest(BaseModel):
    speaker_role: Literal["candidate", "interviewer"]
    started_at_seconds: float = Field(ge=0)
    ended_at_seconds: float = Field(ge=0)
    text: str = Field(min_length=1, max_length=5000)

    @field_validator("ended_at_seconds")
    @classmethod
    def end_after_start(cls, value: float, info):
        start = info.data.get("started_at_seconds")
        if start is not None and value <= start:
            raise ValueError("ended_at_seconds must be after started_at_seconds")
        return value


class MockTranscriptImportRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)
    segments: list[MockTranscriptSegmentRequest] = Field(min_length=2, max_length=500)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise ValueError("Reason must contain at least 10 non-space characters")
        return value
