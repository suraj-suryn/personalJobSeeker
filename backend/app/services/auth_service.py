import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import AdminUserCreate, LoginRequest, Token, UserResponse

logger = logging.getLogger(__name__)
settings = get_settings()


async def create_user(db: AsyncSession, data: AdminUserCreate) -> User:
    """Create a new user. Only called by admin."""
    # Check email uniqueness
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email {data.email} is already registered",
        )

    user = User(
        email=data.email,
        name=data.name,
        hashed_password=hash_password(data.password),
        role=UserRole(data.role),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    logger.info("Created user: %s (role=%s)", user.email, user.role)
    return user


async def authenticate_user(db: AsyncSession, data: LoginRequest) -> Token:
    """Verify credentials and return a JWT token."""
    from fastapi import HTTPException, status

    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Contact admin.",
        )

    token, expires_in = create_access_token(subject=user.id, role=user.role.value)
    return Token(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User:
    """Fetch a user by ID. Raises 404 if not found."""
    from fastapi import HTTPException, status

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def ensure_admin_exists(db: AsyncSession) -> None:
    """
    Seed the admin account on first startup if it doesn't exist.
    Called from the FastAPI lifespan hook.
    """
    result = await db.execute(select(User).where(User.email == settings.admin_email))
    if result.scalar_one_or_none():
        return

    admin = User(
        email=settings.admin_email,
        name=settings.admin_name,
        hashed_password=hash_password(settings.admin_password),
        role=UserRole.admin,
        is_active=True,
    )
    db.add(admin)
    await db.commit()
    logger.info("Admin account created: %s", settings.admin_email)


async def list_all_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


async def toggle_user_active(db: AsyncSession, user_id: uuid.UUID, active: bool) -> User:
    user = await get_user_by_id(db, user_id)
    user.is_active = active
    await db.flush()
    await db.refresh(user)
    return user


async def update_user_settings(db: AsyncSession, user_id: uuid.UUID, **kwargs) -> User:
    user = await get_user_by_id(db, user_id)
    for key, value in kwargs.items():
        if value is not None and hasattr(user, key):
            setattr(user, key, value)
    await db.flush()
    await db.refresh(user)
    return user
