"""
Tests for resume upload, parsing, and versioning endpoints.
"""

import io
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User, UserRole


async def _get_token(client: AsyncClient, email: str, db: AsyncSession) -> str:
    user = User(email=email, name="Resume Tester", hashed_password=hash_password("Pass1234"), role=UserRole.user)
    db.add(user)
    await db.flush()
    resp = await client.post("/v1/auth/login", json={"email": email, "password": "Pass1234"})
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_upload_resume_invalid_format(client: AsyncClient, db_session: AsyncSession):
    """PNG file should be rejected."""
    token = await _get_token(client, "resume-bad@ex.com", db_session)
    fake_png = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    resp = await client.post(
        "/v1/resumes/upload",
        files={"file": ("resume.png", fake_png, "image/png")},
        data={"is_primary": "true"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_resumes_empty(client: AsyncClient, db_session: AsyncSession):
    token = await _get_token(client, "resume-empty@ex.com", db_session)
    resp = await client.get("/v1/resumes/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_resume_not_found(client: AsyncClient, db_session: AsyncSession):
    token = await _get_token(client, "resume-404@ex.com", db_session)
    resp = await client.get(
        "/v1/resumes/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_resume_not_found(client: AsyncClient, db_session: AsyncSession):
    token = await _get_token(client, "resume-del@ex.com", db_session)
    resp = await client.delete(
        "/v1/resumes/00000000-0000-0000-0000-000000000000",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
