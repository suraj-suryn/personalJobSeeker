import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JobMatch(Base):
    __tablename__ = "job_matches"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", "resume_id", name="uq_job_match_user_job_resume"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )

    # Score 0.0 – 100.0
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    cosine_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # LLM-generated analysis
    missing_skills: Mapped[list | None] = mapped_column(JSONB, nullable=True)   # ["Python", "Docker"]
    strengths: Mapped[list | None] = mapped_column(JSONB, nullable=True)        # ["5y Python exp"]
    weaknesses: Mapped[list | None] = mapped_column(JSONB, nullable=True)       # ["No AWS experience"]
    summary: Mapped[str | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="job_matches")  # noqa: F821
    job: Mapped["Job"] = relationship("Job", back_populates="job_matches")  # noqa: F821
    resume: Mapped["Resume"] = relationship("Resume", back_populates="job_matches")  # noqa: F821

    def __repr__(self) -> str:
        return f"<JobMatch user={self.user_id} job={self.job_id} score={self.match_score}>"
