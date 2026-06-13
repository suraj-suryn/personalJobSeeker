import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # pdf | docx
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Parsed structured data stored as JSONB
    # Structure: {name, email, phone, skills[], education[], experience[], certifications[], projects[]}
    parsed_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ChromaDB collection ID for this user's resume embeddings
    chroma_collection_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chroma_doc_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    parse_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending | processing | done | failed

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="resumes")  # noqa: F821
    job_matches: Mapped[list["JobMatch"]] = relationship(  # noqa: F821
        "JobMatch", back_populates="resume"
    )
    resume_versions: Mapped[list["ResumeVersion"]] = relationship(  # noqa: F821
        "ResumeVersion", back_populates="resume"
    )
    cover_letters: Mapped[list["CoverLetter"]] = relationship(  # noqa: F821
        "CoverLetter", back_populates="resume"
    )

    def __repr__(self) -> str:
        return f"<Resume id={self.id} filename={self.filename} user={self.user_id}>"
