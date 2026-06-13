from app.services.auth_service import (
    create_user,
    authenticate_user,
    get_user_by_id,
    ensure_admin_exists,
    list_all_users,
    toggle_user_active,
    update_user_settings,
)
from app.services.resume_service import (
    save_and_parse_resume,
    get_resume,
    list_resumes,
    get_primary_resume,
    delete_resume,
)
from app.services.job_service import (
    get_job,
    list_jobs,
    bulk_upsert_jobs,
    get_recent_jobs,
)
from app.services.email_service import send_email, send_daily_digest
from app.services.notification_service import send_new_jobs_notification, send_desktop_notification
from app.services.vector_service import (
    upsert_resume_embedding,
    upsert_job_embedding,
    query_similar_jobs,
)

__all__ = [
    "create_user", "authenticate_user", "get_user_by_id", "ensure_admin_exists",
    "list_all_users", "toggle_user_active", "update_user_settings",
    "save_and_parse_resume", "get_resume", "list_resumes", "get_primary_resume", "delete_resume",
    "get_job", "list_jobs", "bulk_upsert_jobs", "get_recent_jobs",
    "send_email", "send_daily_digest",
    "send_new_jobs_notification", "send_desktop_notification",
    "upsert_resume_embedding", "upsert_job_embedding", "query_similar_jobs",
]
