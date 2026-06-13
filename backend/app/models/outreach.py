import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CoverLetter(Base):
    __tablename__ = "cover_letters"

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

    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    tone: Mapped[str] = mapped_column(String(50), nullable=False, default="professional")

    file_path_pdf: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_path_docx: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="cover_letters")  # noqa: F821
    job: Mapped["Job"] = relationship("Job", back_populates="cover_letters")  # noqa: F821
    resume: Mapped["Resume"] = relationship("Resume", back_populates="cover_letters")  # noqa: F821
    application: Mapped[list["Application"]] = relationship(  # noqa: F821
        "Application", back_populates="cover_letter", foreign_keys="Application.cover_letter_id"
    )

    def __repr__(self) -> str:
        return f"<CoverLetter id={self.id} job={self.job_id}>"


class OutreachMessage(Base):
    __tablename__ = "outreach_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )

    message_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # linkedin_message | email_draft | follow_up
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)  # for email drafts
    recipient_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="outreach_messages")  # noqa: F821
    job: Mapped["Job"] = relationship("Job", back_populates="outreach_messages")  # noqa: F821

    def __repr__(self) -> str:
        return f"<OutreachMessage type={self.message_type} job={self.job_id}>"
