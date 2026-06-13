import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="userrole"), nullable=False, default=UserRole.user
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # LLM provider preference (per-user, all zero-cost options)
    llm_provider: Mapped[str] = mapped_column(
        String(50), nullable=False, default="ollama"
    )  # ollama | openrouter | groq | gemini

    # Notification preferences
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    desktop_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    match_threshold: Mapped[int] = mapped_column(nullable=False, default=65)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    resumes: Mapped[list["Resume"]] = relationship(  # noqa: F821
        "Resume", back_populates="user", cascade="all, delete-orphan"
    )
    job_matches: Mapped[list["JobMatch"]] = relationship(  # noqa: F821
        "JobMatch", back_populates="user", cascade="all, delete-orphan"
    )
    applications: Mapped[list["Application"]] = relationship(  # noqa: F821
        "Application", back_populates="user", cascade="all, delete-orphan"
    )
    resume_versions: Mapped[list["ResumeVersion"]] = relationship(  # noqa: F821
        "ResumeVersion", back_populates="user", cascade="all, delete-orphan"
    )
    cover_letters: Mapped[list["CoverLetter"]] = relationship(  # noqa: F821
        "CoverLetter", back_populates="user", cascade="all, delete-orphan"
    )
    outreach_messages: Mapped[list["OutreachMessage"]] = relationship(  # noqa: F821
        "OutreachMessage", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
