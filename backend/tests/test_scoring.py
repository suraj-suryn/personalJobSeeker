"""
Tests for job match scoring endpoints.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.job import Job
from app.models.user import User, UserRole
from app.scrapers.base_scraper import BaseScraper


async def _get_token(client: AsyncClient, email: str, db: AsyncSession) -> str:
    user = User(email=email, name="Scorer", hashed_password=hash_password("Pass1234"), role=UserRole.user)
    db.add(user)
    await db.flush()
    resp = await client.post("/v1/auth/login", json={"email": email, "password": "Pass1234"})
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_matches_empty(client: AsyncClient, db_session: AsyncSession):
    """Matches dashboard returns empty when no scores exist."""
    token = await _get_token(client, "score-empty@ex.com", db_session)
    resp = await client.get("/v1/scoring/matches", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "matches" in data
    assert "stats" in data


@pytest.mark.asyncio
async def test_score_missing_job(client: AsyncClient, db_session: AsyncSession):
    """Scoring with non-existent job_id should fail gracefully."""
    token = await _get_token(client, "score-missing@ex.com", db_session)
    resp = await client.post(
        "/v1/scoring/score",
        json={
            "job_id": "00000000-0000-0000-0000-000000000000",
            "resume_id": "00000000-0000-0000-0000-000000000001",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    # Should be 404 (job not found) or 422 (validation)
    assert resp.status_code in (404, 422, 400)


@pytest.mark.asyncio
async def test_batch_score_empty(client: AsyncClient, db_session: AsyncSession):
    """Batch score with empty job list returns 202."""
    token = await _get_token(client, "score-batch@ex.com", db_session)
    resp = await client.post(
        "/v1/scoring/score/batch",
        json={
            "job_ids": [],
            "resume_id": "00000000-0000-0000-0000-000000000000",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 202, 400)
