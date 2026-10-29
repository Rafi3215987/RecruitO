from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    # True for accounts created on the candidate's behalf (manager CV import)
    # that still need the candidate to set a password via an emailed invite.
    password_pending: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    candidate_profile: Mapped[CandidateProfile | None] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    interviewer_profile: Mapped[InterviewerProfile | None] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    # A user_id primary key means each user can have at most one profile.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    contact_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    phone_number: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    certificate_full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    education_qualification: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    institution_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    department: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    graduation_year: Mapped[int | None] = mapped_column(nullable=True)
    resume_storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resume_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped[User] = relationship(back_populates="candidate_profile")


class InterviewerProfile(Base):
    __tablename__ = "interviewer_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    institute: Mapped[str | None] = mapped_column(String(255), nullable=True)
    experience_years: Mapped[int | None] = mapped_column(nullable=True)
    experience_summary: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    education: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    photo_storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped[User] = relationship(back_populates="interviewer_profile")
