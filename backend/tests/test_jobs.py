"""
Tests for job search and listing endpoints.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.job import Job
from app.models.user import User, UserRole
from app.scrapers.base_scraper import BaseScraper


async def _get_token(client: AsyncClient, email: str, password: str, db: AsyncSession) -> str:
    user = User(email=email, name="Job Tester", hashed_password=hash_password(password), role=UserRole.user)
    db.add(user)
    await db.flush()
    resp = await client.post("/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_list_jobs_empty(client: AsyncClient, db_session: AsyncSession):
    token = await _get_token(client, "jobs-list@ex.com", "Pass1234", db_session)
    resp = await client.get("/v1/jobs/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "jobs" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_list_jobs_with_data(client: AsyncClient, db_session: AsyncSession):
    """Insert sample jobs, verify they appear in listing."""
    token = await _get_token(client, "jobs-data@ex.com", "Pass1234", db_session)

    for i in range(3):
        url = f"https://example.com/job/{i}"
        db_session.add(Job(
            title=f"Python Dev {i}",
            company="TechCo",
            url=url,
            url_hash=BaseScraper.make_url_hash(url),
            source="test",
        ))
    await db_session.flush()

    resp = await client.get("/v1/jobs/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 3


@pytest.mark.asyncio
async def test_get_job_not_found(client: AsyncClient, db_session: AsyncSession):
    token = await _get_token(client, "jobs-notfound@ex.com", "Pass1234", db_session)
    resp = await client.get("/v1/jobs/00000000-0000-0000-0000-000000000000", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_job_found(client: AsyncClient, db_session: AsyncSession):
    token = await _get_token(client, "jobs-found@ex.com", "Pass1234", db_session)
    url = "https://example.com/found-job"
    job = Job(title="Found Job", company="Co", url=url, url_hash=BaseScraper.make_url_hash(url), source="test")
    db_session.add(job)
    await db_session.flush()

    resp = await client.get(f"/v1/jobs/{job.id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Found Job"


@pytest.mark.asyncio
async def test_jobs_pagination(client: AsyncClient, db_session: AsyncSession):
    token = await _get_token(client, "jobs-page@ex.com", "Pass1234", db_session)

    for i in range(15):
        url = f"https://example.com/page-job/{i}"
        db_session.add(Job(
            title=f"Paginated Job {i}",
            company="Paged Co",
            url=url,
            url_hash=BaseScraper.make_url_hash(url),
            source="test",
        ))
    await db_session.flush()

    resp = await client.get("/v1/jobs/?page=1&page_size=5", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["jobs"]) <= 5
