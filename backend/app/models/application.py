import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ApplicationStatus(str, enum.Enum):
    saved = "saved"
    applied = "applied"
    interviewing = "interviewing"
    offer = "offer"
    rejected = "rejected"
    withdrawn = "withdrawn"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resume_versions.id", ondelete="SET NULL"), nullable=True
    )
    cover_letter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cover_letters.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="applicationstatus"),
        nullable=False,
        default=ApplicationStatus.saved,
    )

    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform: Mapped[str | None] = mapped_column(String(100), nullable=True)  # where applied

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="applications")  # noqa: F821
    job: Mapped["Job"] = relationship("Job", back_populates="applications")  # noqa: F821
    resume_version: Mapped["ResumeVersion | None"] = relationship(  # noqa: F821
        "ResumeVersion", back_populates="application", foreign_keys=[resume_version_id]
    )
    cover_letter: Mapped["CoverLetter | None"] = relationship(  # noqa: F821
        "CoverLetter", back_populates="application", foreign_keys=[cover_letter_id]
    )

    def __repr__(self) -> str:
        return f"<Application user={self.user_id} job={self.job_id} status={self.status}>"
