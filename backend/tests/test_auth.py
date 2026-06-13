"""
Tests for authentication endpoints.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful login returns JWT token."""
    user = User(
        email="testuser@example.com",
        name="Test User",
        hashed_password=hash_password("TestPass1"),
        role=UserRole.user,
    )
    db_session.add(user)
    await db_session.flush()

    resp = await client.post("/v1/auth/login", json={
        "email": "testuser@example.com",
        "password": "TestPass1",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["email"] == "testuser@example.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, db_session: AsyncSession):
    """Test that wrong password returns 401."""
    user = User(
        email="testuser2@example.com",
        name="Test User 2",
        hashed_password=hash_password("CorrectPass1"),
        role=UserRole.user,
    )
    db_session.add(user)
    await db_session.flush()

    resp = await client.post("/v1/auth/login", json={
        "email": "testuser2@example.com",
        "password": "WrongPassword1",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with non-existent email returns 401."""
    resp = await client.post("/v1/auth/login", json={
        "email": "nobody@example.com",
        "password": "SomePass1",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    """Test /me without token returns 403."""
    resp = await client.get("/v1/auth/me")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_me_with_token(client: AsyncClient, db_session: AsyncSession):
    """Test /me returns user data with valid token."""
    user = User(
        email="meto@example.com",
        name="Me User",
        hashed_password=hash_password("MePass1"),
        role=UserRole.user,
    )
    db_session.add(user)
    await db_session.flush()

    login = await client.post("/v1/auth/login", json={
        "email": "meto@example.com",
        "password": "MePass1",
    })
    token = login.json()["access_token"]

    resp = await client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "meto@example.com"


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test the health check endpoint."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
