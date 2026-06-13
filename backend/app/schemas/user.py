import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    email_notifications: bool | None = None
    desktop_notifications: bool | None = None
    match_threshold: int | None = Field(None, ge=0, le=100)
    llm_provider: str | None = Field(None, pattern="^(ollama|openrouter|groq|gemini|openai)$")


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    role: str
    is_active: bool
    llm_provider: str
    email_notifications: bool
    desktop_notifications: bool
    match_threshold: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUserCreate(BaseModel):
    """Admin-only endpoint: create a new user account."""
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="user", pattern="^(admin|user)$")

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        return v


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
