from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    seniority: Mapped[str] = mapped_column(
        String(60), nullable=False, default="Unspecified", server_default="Unspecified"
    )
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    jd_text: Mapped[str] = mapped_column(Text, nullable=False)
    external_post_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    external_post_provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    blogger_post_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    requirements: Mapped[list["JobRequirement"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", name="fk_jobs_created_by_id_users"),
        nullable=True,
    )
