from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint(
            "candidate_id",
            "job_id",
            name="uq_applications_candidate_job",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="submitted",
        nullable=False,
    )
    candidate_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    education_qualification: Mapped[str | None] = mapped_column(String(255), nullable=True)
    institution_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    graduation_year: Mapped[int | None] = mapped_column(nullable=True)
    resume_storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resume_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scheduling_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="not_queued", server_default="not_queued", index=True,
    )
    scheduling_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    scheduling_processing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduling_next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    scheduling_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    candidate_removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
