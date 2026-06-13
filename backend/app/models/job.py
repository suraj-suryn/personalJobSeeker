import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("url_hash", name="uq_jobs_url_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Core fields
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_type: Mapped[str | None] = mapped_column(String(100), nullable=True)  # remote, onsite, hybrid
    experience_level: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Salary
    salary_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Content
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Source
    url: Mapped[str] = mapped_column(Text, nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # SHA256 of normalized URL
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # linkedin | indeed | wellfound | naukri | company

    # Timing
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ChromaDB doc ID for job description embedding
    chroma_doc_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    job_matches: Mapped[list["JobMatch"]] = relationship(  # noqa: F821
        "JobMatch", back_populates="job", cascade="all, delete-orphan"
    )
    applications: Mapped[list["Application"]] = relationship(  # noqa: F821
        "Application", back_populates="job", cascade="all, delete-orphan"
    )
    resume_versions: Mapped[list["ResumeVersion"]] = relationship(  # noqa: F821
        "ResumeVersion", back_populates="job"
    )
    cover_letters: Mapped[list["CoverLetter"]] = relationship(  # noqa: F821
        "CoverLetter", back_populates="job"
    )
    outreach_messages: Mapped[list["OutreachMessage"]] = relationship(  # noqa: F821
        "OutreachMessage", back_populates="job"
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id} title={self.title} company={self.company}>"
