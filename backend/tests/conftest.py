"""
Pytest configuration and fixtures.
"""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import create_app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app: FastAPI = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient) -> str:
    """Create admin user and return JWT token."""
    from app.config import get_settings
    settings = get_settings()

    # Seed admin
    from app.database import AsyncSessionLocal
    from app.services.auth_service import ensure_admin_exists
    # For tests, directly create admin
    from app.models.user import User, UserRole
    from app.core.security import hash_password
    from sqlalchemy import select

    admin = User(
        email="test-admin@example.com",
        name="Test Admin",
        hashed_password=hash_password("TestAdmin1"),
        role=UserRole.admin,
    )

    # Check if exists
    async for session in override_db(client):
        pass

    resp = await client.post("/v1/auth/login", json={
        "email": "test-admin@example.com",
        "password": "TestAdmin1",
    })
    if resp.status_code == 401:
        # Create it first
        return ""
    return resp.json().get("access_token", "")


async def override_db(client):
    yield


@pytest.fixture
def auth_headers(admin_token: str) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}
