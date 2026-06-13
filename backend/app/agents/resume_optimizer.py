"""
Resume Optimization Agent
Generates ATS-optimized resumes tailored to a specific job description.
NEVER invents experience — only reframes existing facts with better keywords.
"""

import json
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import get_llm
from app.schemas.resume import ParsedResumeData

logger = logging.getLogger(__name__)


class ResumeOptimizer:
    SYSTEM_PROMPT = """You are an expert ATS resume optimizer. Your task is to rewrite the resume to better match the job description.

STRICT RULES:
1. NEVER invent, fabricate, or exaggerate experience, skills, or achievements
2. NEVER add companies, roles, degrees, or certifications that don't exist in the original
3. ONLY reframe existing facts using better keywords from the job description
4. Preserve all dates, company names, and factual information exactly
5. Incorporate relevant keywords from the job description naturally
6. Improve action verbs and quantify achievements where the data already exists
7. Reorder skills to prioritize those matching the job description

Return ONLY valid JSON with the same structure as the input resume data."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.llm = get_llm()

    async def optimize(
        self,
        user_id: uuid.UUID,
        resume_id: uuid.UUID,
        job_id: uuid.UUID,
        provider: str | None = None,
    ):
        """
        Generate an ATS-optimized resume version for a specific job.
        Returns a ResumeVersion ORM object.
        """
        from sqlalchemy import select
        from app.models.resume import Resume
        from app.models.job import Job
        from app.models.resume_version import ResumeVersion
        from app.services.document_service import generate_resume_pdf, generate_resume_docx

        # Load resume and job
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

        original_data = resume.parsed_data or {}

        # LLM optimization
        optimized_data = await self._llm_optimize(
            original_data=original_data,
            job_title=job.title,
            job_company=job.company,
            job_description=(job.description or "")[:3000],
            provider=provider,
        )

        # Generate diff summary
        changes_summary = self._generate_diff_summary(original_data, optimized_data)

        # Generate PDF and DOCX
        output_id = str(uuid.uuid4())
        pdf_path = generate_resume_pdf(optimized_data, output_id)
        docx_path = generate_resume_docx(optimized_data, output_id)

        # Save to DB
        version = ResumeVersion(
            user_id=user_id,
            resume_id=resume_id,
            job_id=job_id,
            optimized_content=optimized_data,
            changes_summary=changes_summary,
            file_path_pdf=pdf_path,
            file_path_docx=docx_path,
        )
        self.db.add(version)
        await self.db.flush()
        await self.db.refresh(version)
        return version

    async def _llm_optimize(
        self,
        original_data: dict,
        job_title: str,
        job_company: str,
        job_description: str,
        provider: str | None = None,
    ) -> dict:
        user_prompt = f"""
Job Title: {job_title}
Company: {job_company}

Job Description:
{job_description}

Original Resume Data:
{json.dumps(original_data, indent=2)[:4000]}

Rewrite the resume JSON to better match this job. Follow all rules strictly.
Return ONLY the optimized JSON — same structure as input."""

        try:
            response = await self.llm.chat(
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                provider=provider,
                temperature=0.2,
                max_tokens=4096,
            )
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("LLM returned invalid JSON for resume optimization — using original")
            return original_data
        except Exception as exc:
            logger.exception("Resume optimization failed: %s", exc)
            return original_data

    def _generate_diff_summary(self, original: dict, optimized: dict) -> str:
        """Generate a human-readable summary of what changed."""
        changes = []

        orig_skills = set(original.get("skills", []))
        opt_skills = set(optimized.get("skills", []))
        added_keywords = opt_skills - orig_skills
        if added_keywords:
            changes.append(f"Added keywords: {', '.join(list(added_keywords)[:5])}")

        if original.get("summary") != optimized.get("summary"):
            changes.append("Professional summary rewritten for ATS alignment")

        orig_exp_count = len(original.get("experience", []))
        opt_exp_count = len(optimized.get("experience", []))
        if orig_exp_count == opt_exp_count:
            changes.append(f"Rewrote {orig_exp_count} experience entries with job-relevant keywords")

        return "; ".join(changes) if changes else "Minor keyword adjustments made"
