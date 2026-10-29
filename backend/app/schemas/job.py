from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Literal

class JobGenerateRequest(BaseModel):
    role_title: str
    seniority: str
    key_skills: list[str] = Field(min_length=1)
    employment_type: str
    location_mode: str


class JobGenerateResponse(BaseModel):
    job_id: int
    status: str

class JobRequirementUpdate(BaseModel):
    text: str
    kind: Literal["required", "preferred"]
    category: Literal["skills", "experience", "qualification"]
    weight: int = Field(ge=1, le=5)


class JobUpdateRequest(BaseModel):
    jd_text: str
    requirements: list[JobRequirementUpdate]
    external_post_url: str | None = Field(default=None, max_length=2048)

    @field_validator("external_post_url")
    @classmethod
    def validate_external_post_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        from urllib.parse import urlparse

        value = value.strip()
        parsed = urlparse(value)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not host or parsed.username or parsed.password:
            raise ValueError("Enter a valid HTTPS URL for the external job post")
        return value


class JobRequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    kind: str
    category: str
    weight: int


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    seniority: str
    status: str
    jd_text: str
    external_post_url: str | None
    external_post_provider: str | None
    contact_email: str | None
    created_at: datetime
    requirements: list[JobRequirementResponse]

class JobListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    seniority: str
    status: str
    created_at: datetime

class PublicJobItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    seniority: str
    external_post_url: str | None
    external_post_provider: str | None
    created_at: datetime
