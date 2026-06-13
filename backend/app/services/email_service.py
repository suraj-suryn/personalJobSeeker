"""
Email notification service using aiosmtplib (Gmail SMTP or any SMTP server).
All notification sending is zero-cost.
"""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_email(
    to_addresses: list[str],
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> bool:
    """Send an email via SMTP. Returns True on success, False on failure."""
    if not settings.email_configured:
        logger.debug("Email not configured — skipping send to %s", to_addresses)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_username}>"
    msg["To"] = ", ".join(to_addresses)

    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            start_tls=True,
        )
        logger.info("Email sent to %s: %s", to_addresses, subject)
        return True
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to_addresses, exc)
        return False


async def send_new_jobs_notification(jobs: list[dict]) -> None:
    """Send a notification email about newly discovered matching jobs."""
    if not jobs or not settings.notification_email:
        return

    job_items = ""
    for j in jobs[:20]:  # Cap at 20 per email
        salary = ""
        if j.get("salary_min") and j.get("salary_max"):
            salary = f" — {j['salary_currency'] or '$'}{j['salary_min']:,.0f}–{j['salary_max']:,.0f}"
        job_items += f"""
        <tr>
            <td style="padding:8px; border-bottom:1px solid #eee;">
                <a href="{j.get('url', '#')}" style="color:#2563eb; text-decoration:none; font-weight:600;">
                    {j.get('title', 'Unknown Title')}
                </a>
            </td>
            <td style="padding:8px; border-bottom:1px solid #eee;">{j.get('company', '')}</td>
            <td style="padding:8px; border-bottom:1px solid #eee;">{j.get('location', 'Remote')}{salary}</td>
            <td style="padding:8px; border-bottom:1px solid #eee; color:#6b7280; font-size:12px;">
                {j.get('source', '').title()}
            </td>
        </tr>"""

    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color: #1f2937; max-width: 700px; margin: auto; padding: 20px;">
        <h2 style="color: #2563eb;">🔔 {len(jobs)} New Job{'s' if len(jobs) > 1 else ''} Found</h2>
        <p style="color: #6b7280;">New jobs matching your search preferences were just discovered.</p>
        <table style="width:100%; border-collapse:collapse; margin-top:16px;">
            <thead>
                <tr style="background:#f3f4f6;">
                    <th style="padding:8px; text-align:left;">Title</th>
                    <th style="padding:8px; text-align:left;">Company</th>
                    <th style="padding:8px; text-align:left;">Location / Salary</th>
                    <th style="padding:8px; text-align:left;">Source</th>
                </tr>
            </thead>
            <tbody>{job_items}</tbody>
        </table>
        <p style="margin-top:24px;">
            <a href="http://localhost" style="background:#2563eb; color:white; padding:10px 20px; border-radius:6px; text-decoration:none; font-weight:600;">
                View All Jobs →
            </a>
        </p>
        <p style="color:#9ca3af; font-size:12px; margin-top:32px;">
            PersonalJobSeeker • You're receiving this because job alerts are enabled.
        </p>
    </body>
    </html>"""

    await send_email(
        to_addresses=[settings.notification_email],
        subject=f"[JobSeeker] {len(jobs)} New Job{'s' if len(jobs) > 1 else ''} Found",
        html_body=html,
    )


async def send_daily_digest(db) -> None:
    """Send a daily summary email of top matched jobs."""
    from sqlalchemy import select, desc
    from app.models.job_match import JobMatch
    from app.models.job import Job

    if not settings.notification_email:
        return

    result = await db.execute(
        select(JobMatch, Job)
        .join(Job, JobMatch.job_id == Job.id)
        .order_by(desc(JobMatch.match_score))
        .limit(10)
    )
    rows = result.all()

    if not rows:
        return

    job_items = ""
    for match, job in rows:
        score_color = "#16a34a" if match.match_score >= 80 else "#d97706" if match.match_score >= 60 else "#dc2626"
        job_items += f"""
        <tr>
            <td style="padding:8px; border-bottom:1px solid #eee;">
                <a href="{job.url}" style="color:#2563eb;">{job.title}</a>
            </td>
            <td style="padding:8px; border-bottom:1px solid #eee;">{job.company}</td>
            <td style="padding:8px; border-bottom:1px solid #eee; font-weight:700; color:{score_color};">
                {match.match_score:.0f}%
            </td>
        </tr>"""

    html = f"""<!DOCTYPE html><html><body style="font-family:sans-serif; max-width:600px; margin:auto; padding:20px;">
    <h2 style="color:#2563eb;">📊 Daily Job Match Digest</h2>
    <p>Your top {len(rows)} job matches as of today:</p>
    <table style="width:100%; border-collapse:collapse;">
        <thead><tr style="background:#f3f4f6;">
            <th style="padding:8px; text-align:left;">Job</th>
            <th style="padding:8px; text-align:left;">Company</th>
            <th style="padding:8px; text-align:left;">Match</th>
        </tr></thead>
        <tbody>{job_items}</tbody>
    </table>
    <p style="margin-top:20px;">
        <a href="http://localhost/dashboard" style="background:#2563eb; color:white; padding:10px 20px; border-radius:6px; text-decoration:none;">
            Open Dashboard →
        </a>
    </p>
    </body></html>"""

    await send_email(
        to_addresses=[settings.notification_email],
        subject="[JobSeeker] Daily Match Digest",
        html_body=html,
    )
