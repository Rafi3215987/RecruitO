from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Interview(Base):
    __tablename__ = "interviews"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_interviews_token_hash"),
        UniqueConstraint("interviewer_token_hash", name="uq_interviews_interviewer_token_hash"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
    )
    interviewer_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", name="fk_interviews_interviewer_id_users", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="scheduled",
        nullable=False,
    )
    token_hash: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    interviewer_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    interviewer_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    candidate_joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    calendar_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_started", server_default="not_started", index=True)
    analysis_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    analysis_processing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    analysis_next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    analysis_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    manager_removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
