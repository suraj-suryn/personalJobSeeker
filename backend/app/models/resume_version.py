import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ResumeVersion(Base):
    """ATS-optimized resume tailored for a specific job."""

    __tablename__ = "resume_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Optimized content as structured JSON (same shape as resume.parsed_data)
    optimized_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Diff summary of changes made
    changes_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Generated file paths
    file_path_pdf: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_path_docx: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="resume_versions")  # noqa: F821
    resume: Mapped["Resume"] = relationship("Resume", back_populates="resume_versions")  # noqa: F821
    job: Mapped["Job"] = relationship("Job", back_populates="resume_versions")  # noqa: F821
    application: Mapped[list["Application"]] = relationship(  # noqa: F821
        "Application", back_populates="resume_version", foreign_keys="Application.resume_version_id"
    )

    def __repr__(self) -> str:
        return f"<ResumeVersion id={self.id} job={self.job_id}>"
