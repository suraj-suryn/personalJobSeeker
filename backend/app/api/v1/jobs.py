import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.database import get_db
from app.schemas.job import JobListResponse, JobResponse, JobSearchRequest, JobSearchStatus
from app.services.job_service import get_job, list_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])

# In-memory task tracker for background searches
_search_tasks: dict[str, dict] = {}


@router.post("/search", response_model=JobSearchStatus, status_code=202)
async def trigger_job_search(
    body: JobSearchRequest,
    background_tasks: BackgroundTasks,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger an async job search across the specified boards.
    Returns a task_id to poll for status.
    """
    task_id = str(uuid.uuid4())
    _search_tasks[task_id] = {"status": "queued", "jobs_found": 0, "sources_completed": []}

    async def _run() -> None:
        from app.database import AsyncSessionLocal
        from app.agents.job_search_agent import JobSearchAgent

        _search_tasks[task_id]["status"] = "running"
        async with AsyncSessionLocal() as session:
            agent = JobSearchAgent(session)
            inserted, _ = await agent.search(
                query=body.query,
                location=body.location,
                sources=body.sources,
                max_per_source=body.max_results,
            )
            _search_tasks[task_id]["status"] = "done"
            _search_tasks[task_id]["jobs_found"] = inserted
            _search_tasks[task_id]["sources_completed"] = body.sources

    background_tasks.add_task(_run)
    return JobSearchStatus(task_id=task_id, status="queued", message="Search started")


@router.get("/search/status/{task_id}", response_model=JobSearchStatus)
async def get_search_status(task_id: str):
    task = _search_tasks.get(task_id)
    if not task:
        from fastapi import HTTPException
        raise HTTPException(404, "Task not found")
    return JobSearchStatus(
        task_id=task_id,
        status=task["status"],
        jobs_found=task["jobs_found"],
        sources_completed=task["sources_completed"],
    )


@router.get("/", response_model=JobListResponse)
async def list_all_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    query: str | None = Query(default=None),
    source: str | None = Query(default=None),
    location: str | None = Query(default=None),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all scraped jobs with optional filters and pagination."""
    jobs, total = await list_jobs(db, page, page_size, query, source, location)
    return JobListResponse(
        jobs=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_single_job(
    job_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    job = await get_job(db, job_id)
    return JobResponse.model_validate(job)


@router.get("/recent/new")
async def get_recent_jobs(
    hours: int = Query(default=6, ge=1, le=48),
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get jobs first seen in the last N hours (real-time feed)."""
    from app.services.job_service import get_recent_jobs as _get_recent
    jobs = await _get_recent(db, hours=hours, limit=50)
    return [JobResponse.model_validate(j) for j in jobs]
