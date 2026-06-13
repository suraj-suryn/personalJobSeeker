from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "production", "test"] = "development"
    app_secret_key: str = "change-this-secret-min-32-chars"
    app_allowed_origins: str = "http://localhost:3000,http://localhost"

    # Admin account (auto-seeded on first startup)
    admin_email: str = "admin@example.com"
    admin_password: str = "change-this-admin-password"
    admin_name: str = "Admin"

    # Database
    database_url: str = "postgresql+asyncpg://jobseeker:jobseeker_pass@localhost:5432/jobseeker"

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8001

    # JWT
    jwt_secret_key: str = "change-this-jwt-secret-min-32-chars"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7

    # LLM — Ollama (local, free)
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "llama3.1:8b"
    ollama_embed_model: str = "nomic-embed-text"

    # LLM — OpenRouter (online, free tier)
    openrouter_api_key: str = ""
    openrouter_free_model: str = "meta-llama/llama-3.1-8b-instruct:free"

    # LLM — Groq (online, free tier: 14,400 req/day)
    groq_api_key: str = ""
    groq_free_model: str = "llama-3.1-8b-instant"

    # LLM — Google Gemini (online, free tier: 1M tokens/day)
    gemini_api_key: str = ""
    gemini_free_model: str = "gemini-1.5-flash"

    # LLM — OpenAI (paid, optional upgrade)
    openai_api_key: str = ""

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_name: str = "JobSeeker Alert"
    notification_email: str = ""

    # Job Search
    job_search_interval_minutes: int = 15
    default_match_threshold: int = 65
    max_jobs_per_search: int = 50

    # File Storage
    upload_dir: str = "/app/uploads"
    generated_dir: str = "/app/generated"
    max_upload_size_mb: int = 10

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.app_allowed_origins.split(",") if o.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def email_configured(self) -> bool:
        return bool(self.smtp_username and self.smtp_password)


@lru_cache
def get_settings() -> Settings:
    return Settings()
