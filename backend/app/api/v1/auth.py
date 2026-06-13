import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import get_current_user_id, require_admin
from app.schemas.user import AdminUserCreate, LoginRequest, Token, UserResponse, UserUpdate
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Authenticate with email + password. Returns JWT access token."""
    return await auth_service.authenticate_user(db, body)


@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get the currently authenticated user's profile."""
    user = await auth_service.get_user_by_id(db, user_id)
    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update current user's settings (notifications, LLM provider, etc.)."""
    user = await auth_service.update_user_settings(
        db, user_id,
        **body.model_dump(exclude_none=True),
    )
    return UserResponse.model_validate(user)


# ─── Admin-only endpoints ──────────────────────────────────────────────────

@router.get("/admin/users", response_model=list[UserResponse])
async def admin_list_users(
    admin_id: Annotated[uuid.UUID, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """[Admin] List all users."""
    users = await auth_service.list_all_users(db)
    return [UserResponse.model_validate(u) for u in users]


@router.post("/admin/users", response_model=UserResponse, status_code=201)
async def admin_create_user(
    body: AdminUserCreate,
    admin_id: Annotated[uuid.UUID, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """[Admin] Create a new user account."""
    user = await auth_service.create_user(db, body)
    return UserResponse.model_validate(user)


@router.patch("/admin/users/{user_id}/toggle-active", response_model=UserResponse)
async def admin_toggle_user(
    user_id: uuid.UUID,
    active: bool,
    admin_id: Annotated[uuid.UUID, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """[Admin] Enable or disable a user account."""
    user = await auth_service.toggle_user_active(db, user_id, active)
    return UserResponse.model_validate(user)
