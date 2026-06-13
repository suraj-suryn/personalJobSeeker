"""
Cover Letter Generator Agent
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import get_llm

logger = logging.getLogger(__name__)


class CoverLetterAgent:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.llm = get_llm()

    async def generate(
        self,
        user_id: uuid.UUID,
        resume_id: uuid.UUID,
        job_id: uuid.UUID,
        tone: str = "professional",
        provider: str | None = None,
    ):
        """Generate and persist a cover letter. Returns CoverLetter ORM object."""
        from sqlalchemy import select
        from app.models.resume import Resume
        from app.models.job import Job
        from app.models.outreach import CoverLetter
        from app.services.document_service import generate_cover_letter_pdf, generate_cover_letter_docx

        resume_result = await self.db.execute(
            select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
        )
        resume = resume_result.scalar_one_or_none()
        if not resume:
            raise ValueError(f"Resume {resume_id} not found")

        job_result = await self.db.execute(select(Job).where(Job.id == job_id))
        job = job_result.scalar_one_or_none()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        content = await self._generate_content(
            parsed_data=resume.parsed_data or {},
            job_title=job.title,
            job_company=job.company,
            job_description=(job.description or "")[:2000],
            tone=tone,
            provider=provider,
        )

        output_id = str(uuid.uuid4())
        pdf_path = generate_cover_letter_pdf(content, output_id)
        docx_path = generate_cover_letter_docx(content, output_id)

        letter = CoverLetter(
            user_id=user_id,
            job_id=job_id,
            resume_id=resume_id,
            content=content,
            tone=tone,
            file_path_pdf=pdf_path,
            file_path_docx=docx_path,
        )
        self.db.add(letter)
        await self.db.flush()
        await self.db.refresh(letter)
        return letter

    async def _generate_content(
        self,
        parsed_data: dict,
        job_title: str,
        job_company: str,
        job_description: str,
        tone: str,
        provider: str | None = None,
    ) -> str:
        tone_instructions = {
            "professional": "Write in a formal, professional tone. Focus on achievements and skills.",
            "enthusiastic": "Write with genuine enthusiasm for the company and role. Show passion.",
            "concise": "Be concise — maximum 3 paragraphs. Get to the point quickly.",
        }

        name = parsed_data.get("name", "")
        skills = ", ".join((parsed_data.get("skills") or [])[:10])
        recent_exp = ""
        if parsed_data.get("experience"):
            exp = parsed_data["experience"][0]
            recent_exp = f"{exp.get('title', '')} at {exp.get('company', '')}"

        system_prompt = f"""You are an expert cover letter writer. {tone_instructions.get(tone, tone_instructions['professional'])}

Write a compelling cover letter that:
- Opens with a strong hook
- Highlights the candidate's most relevant experience and skills for THIS specific role
- Shows knowledge of the company
- Closes with a clear call to action
- Is 3-4 paragraphs long
- Does NOT start with "I am writing to apply..."
- Does NOT use clichéd phrases like "I am a hard worker" or "team player"

Format: Plain text with paragraph breaks (no headers, no bullet points)."""

        user_prompt = f"""Write a cover letter for:

Candidate: {name}
Most Recent Role: {recent_exp}
Key Skills: {skills}

Job: {job_title} at {job_company}
Job Description:
{job_description}

Write the complete cover letter now."""

        try:
            return await self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                provider=provider,
                temperature=0.7,
                max_tokens=1500,
            )
        except Exception as exc:
            logger.exception("Cover letter generation failed: %s", exc)
            raise


class OutreachAgent:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.llm = get_llm()

    async def generate(
        self,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
        resume_id: uuid.UUID,
        message_type: str,
        recipient_name: str | None = None,
        provider: str | None = None,
    ):
        """Generate an outreach message. Returns OutreachMessage ORM object."""
        from sqlalchemy import select
        from app.models.resume import Resume
        from app.models.job import Job
        from app.models.outreach import OutreachMessage

        resume_result = await self.db.execute(
            select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
        )
        resume = resume_result.scalar_one_or_none()
        job_result = await self.db.execute(select(Job).where(Job.id == job_id))
        job = job_result.scalar_one_or_none()

        if not resume or not job:
            raise ValueError("Resume or Job not found")

        content, subject = await self._generate_message(
            parsed_data=resume.parsed_data or {},
            job=job,
            message_type=message_type,
            recipient_name=recipient_name,
            provider=provider,
        )

        msg = OutreachMessage(
            user_id=user_id,
            job_id=job_id,
            message_type=message_type,
            content=content,
            subject=subject,
            recipient_name=recipient_name,
        )
        self.db.add(msg)
        await self.db.flush()
        await self.db.refresh(msg)
        return msg

    async def _generate_message(
        self,
        parsed_data: dict,
        job,
        message_type: str,
        recipient_name: str | None,
        provider: str | None,
    ) -> tuple[str, str | None]:
        name = parsed_data.get("name", "")
        skills = ", ".join((parsed_data.get("skills") or [])[:8])
        recent_title = ""
        if parsed_data.get("experience"):
            recent_title = parsed_data["experience"][0].get("title", "")

        if message_type == "linkedin_message":
            prompt = f"""Write a short LinkedIn connection message (max 300 chars) from {name} to a recruiter at {job.company}.
The message should mention interest in the {job.title} role.
The candidate's background: {recent_title}, skills in {skills}.
{"Address it to " + recipient_name + "." if recipient_name else ""}
Be personal and specific. No generic phrases."""
            subject = None

        elif message_type == "email_draft":
            prompt = f"""Write a recruiter outreach email from {name} for the {job.title} position at {job.company}.
Candidate background: {recent_title}, skills: {skills}.
{"Addressed to " + recipient_name + "." if recipient_name else ""}
Include: compelling subject line on first line (format: "Subject: ..."), then blank line, then email body.
3-4 paragraphs. Professional and specific."""
            subject = None  # Extracted from response below

        else:  # follow_up
            prompt = f"""Write a follow-up email from {name} checking on the status of their application for {job.title} at {job.company}.
Polite, brief (2 paragraphs). Include subject line on first line as "Subject: ..."."""
            subject = None

        try:
            content = await self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                provider=provider,
                temperature=0.7,
                max_tokens=600,
            )

            # Extract subject from email messages
            if message_type in ("email_draft", "follow_up") and content.startswith("Subject:"):
                lines = content.split("\n", 2)
                subject = lines[0].replace("Subject:", "").strip()
                content = lines[2].strip() if len(lines) > 2 else content

            return content, subject
        except Exception as exc:
            logger.exception("Outreach generation failed: %s", exc)
            raise
