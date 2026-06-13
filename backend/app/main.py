"""
PersonalJobSeeker — FastAPI Application
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.config import get_settings
from app.core.scheduler import start_scheduler, stop_scheduler

settings = get_settings()

# ─── Structured Logging ────────────────────────────────────────────────────

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.DEBUG if settings.is_development else logging.INFO
    )
)
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.DEBUG if settings.is_development else logging.INFO,
)
logger = logging.getLogger(__name__)


# ─── Application Lifespan ──────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup:
      1. Create upload/generated directories
      2. Apply Alembic migrations (if DATABASE_AUTO_MIGRATE=true)
      3. Seed admin account
      4. Pull Ollama models (background, non-blocking)
      5. Start APScheduler

    Shutdown:
      1. Stop scheduler
    """
    logger.info("Starting PersonalJobSeeker...")

    # Create storage directories
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.generated_dir).mkdir(parents=True, exist_ok=True)
    (Path(settings.generated_dir) / "resumes").mkdir(exist_ok=True)
    (Path(settings.generated_dir) / "cover_letters").mkdir(exist_ok=True)

    # Seed admin account
    from app.database import AsyncSessionLocal
    from app.services.auth_service import ensure_admin_exists
    async with AsyncSessionLocal() as db:
        try:
            await ensure_admin_exists(db)
        except Exception as exc:
            logger.warning("Could not seed admin (DB may not be ready): %s", exc)

    # Pull Ollama models in background (non-blocking)
    import asyncio
    asyncio.create_task(_pull_ollama_models())

    # Start job search scheduler
    start_scheduler()
    logger.info("Startup complete. Admin: %s", settings.admin_email)

    yield

    # Shutdown
    stop_scheduler()
    logger.info("PersonalJobSeeker shutdown complete")


async def _pull_ollama_models() -> None:
    """Pull required Ollama models on first startup."""
    import httpx
    models = [settings.ollama_default_model, settings.ollama_embed_model]
    for model in models:
        try:
            async with httpx.AsyncClient(timeout=600.0) as client:
                logger.info("Pulling Ollama model: %s (may take a while on first run)", model)
                response = await client.post(
                    f"{settings.ollama_base_url}/api/pull",
                    json={"name": model, "stream": False},
                )
                if response.status_code == 200:
                    logger.info("Ollama model ready: %s", model)
        except Exception as exc:
            logger.warning("Could not pull Ollama model %s: %s", model, exc)


# ─── App Factory ───────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="PersonalJobSeeker API",
        description="AI-powered job search and application assistant",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routes
    from app.api.v1 import (
        auth_router,
        resumes_router,
        jobs_router,
        scoring_router,
        cover_letter_router,
        outreach_router,
        applications_router,
        automation_router,
        interview_prep_router,
    )

    prefix = "/v1"
    app.include_router(auth_router, prefix=prefix)
    app.include_router(resumes_router, prefix=prefix)
    app.include_router(jobs_router, prefix=prefix)
    app.include_router(scoring_router, prefix=prefix)
    app.include_router(cover_letter_router, prefix=prefix)
    app.include_router(outreach_router, prefix=prefix)
    app.include_router(applications_router, prefix=prefix)
    app.include_router(automation_router, prefix=prefix)
    app.include_router(interview_prep_router, prefix=prefix)

    # WebSocket for automation (included via automation router already)

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "version": "1.0.0"}

    @app.get("/")
    async def root():
        return {
            "app": "PersonalJobSeeker",
            "version": "1.0.0",
            "docs": "/docs",
        }

    return app


app = create_app()
