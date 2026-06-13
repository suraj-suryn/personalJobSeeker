"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2026-06-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("role", sa.Enum("admin", "user", name="userrole"), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("llm_provider", sa.String(50), nullable=False, server_default="ollama"),
        sa.Column("email_notifications", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("desktop_notifications", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("match_threshold", sa.Integer, nullable=False, server_default="65"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # resumes
    op.create_table(
        "resumes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("raw_text", sa.Text, nullable=True),
        sa.Column("parsed_data", postgresql.JSONB, nullable=True),
        sa.Column("chroma_collection_id", sa.String(255), nullable=True),
        sa.Column("chroma_doc_id", sa.String(255), nullable=True),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("parse_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])

    # jobs
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("job_type", sa.String(100), nullable=True),
        sa.Column("experience_level", sa.String(100), nullable=True),
        sa.Column("salary_min", sa.Float, nullable=True),
        sa.Column("salary_max", sa.Float, nullable=True),
        sa.Column("salary_currency", sa.String(10), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("requirements", sa.Text, nullable=True),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("url_hash", sa.String(64), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("scraped_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("chroma_doc_id", sa.String(255), nullable=True),
    )
    op.create_index("ix_jobs_url_hash", "jobs", ["url_hash"], unique=True)
    op.create_index("ix_jobs_title", "jobs", ["title"])
    op.create_index("ix_jobs_company", "jobs", ["company"])

    # job_matches
    op.create_table(
        "job_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_score", sa.Float, nullable=False),
        sa.Column("cosine_score", sa.Float, nullable=True),
        sa.Column("missing_skills", postgresql.JSONB, nullable=True),
        sa.Column("strengths", postgresql.JSONB, nullable=True),
        sa.Column("weaknesses", postgresql.JSONB, nullable=True),
        sa.Column("summary", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_job_matches_user_id", "job_matches", ["user_id"])
    op.create_index("ix_job_matches_job_id", "job_matches", ["job_id"])
    op.create_unique_constraint("uq_job_match_user_job_resume", "job_matches", ["user_id", "job_id", "resume_id"])

    # applications
    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cover_letter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.Enum("saved", "applied", "interviewing", "offer", "rejected", "withdrawn", name="applicationstatus"), nullable=False, server_default="saved"),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("platform", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_applications_user_id", "applications", ["user_id"])

    # resume_versions
    op.create_table(
        "resume_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("optimized_content", postgresql.JSONB, nullable=True),
        sa.Column("changes_summary", sa.Text, nullable=True),
        sa.Column("file_path_pdf", sa.String(500), nullable=True),
        sa.Column("file_path_docx", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # cover_letters
    op.create_table(
        "cover_letters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("tone", sa.String(50), nullable=False, server_default="professional"),
        sa.Column("file_path_pdf", sa.String(500), nullable=True),
        sa.Column("file_path_docx", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # outreach_messages
    op.create_table(
        "outreach_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("recipient_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Add FK constraints for applications (deferred due to circular refs)
    op.create_foreign_key(None, "applications", "resume_versions", ["resume_version_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key(None, "applications", "cover_letters", ["cover_letter_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_table("outreach_messages")
    op.drop_table("cover_letters")
    op.drop_table("resume_versions")
    op.drop_table("applications")
    op.drop_table("job_matches")
    op.drop_table("jobs")
    op.drop_table("resumes")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS applicationstatus")
