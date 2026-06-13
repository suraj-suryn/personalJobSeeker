"""
Interview Preparation Agent
Generates likely interview questions and suggested answers
from the job description and candidate's resume.
"""

import json
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import get_llm

logger = logging.getLogger(__name__)


class InterviewPrepAgent:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.llm = get_llm()

    async def generate_prep(
        self,
        user_id: uuid.UUID,
        resume_id: uuid.UUID,
        job_id: uuid.UUID,
        provider: str | None = None,
    ) -> dict:
        """
        Generate interview prep materials including:
        - Likely technical questions
        - Likely behavioral questions
        - Company-specific questions
        - Suggested answers based on candidate's experience
        - Key talking points
        """
        from sqlalchemy import select
        from app.models.resume import Resume
        from app.models.job import Job

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

        return await self._generate(
            parsed_data=resume.parsed_data or {},
            job_title=job.title,
            job_company=job.company,
            job_description=(job.description or "")[:2500],
            provider=provider,
        )

    async def _generate(
        self,
        parsed_data: dict,
        job_title: str,
        job_company: str,
        job_description: str,
        provider: str | None = None,
    ) -> dict:
        skills = ", ".join((parsed_data.get("skills") or [])[:15])
        experience_summary = []
        for exp in (parsed_data.get("experience") or [])[:3]:
            experience_summary.append(
                f"{exp.get('title', '')} at {exp.get('company', '')}: {exp.get('description', '')[:200]}"
            )

        system_prompt = """You are an expert interview coach. Generate interview prep materials.
Return ONLY valid JSON with this structure:
{
  "technical_questions": [
    {"question": "...", "suggested_answer": "...", "tips": "..."}
  ],
  "behavioral_questions": [
    {"question": "...", "suggested_answer": "...", "star_example": "..."}
  ],
  "company_questions": [
    {"question": "...", "suggested_answer": "..."}
  ],
  "questions_to_ask": ["Question you should ask the interviewer 1", "..."],
  "key_talking_points": ["Point 1", "Point 2"],
  "red_flags_to_address": ["Potential concern and how to address it"]
}
Generate 3-4 questions per category. Make answers specific to the candidate's background."""

        user_prompt = f"""Job: {job_title} at {job_company}

Job Description:
{job_description}

Candidate Skills: {skills}
Candidate Experience:
{chr(10).join(experience_summary)}

Generate comprehensive interview prep materials."""

        try:
            response = await self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                provider=provider,
                temperature=0.5,
                max_tokens=4096,
            )
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.warning("LLM returned invalid JSON for interview prep: %s", exc)
            return {
                "technical_questions": [],
                "behavioral_questions": [],
                "company_questions": [],
                "questions_to_ask": [],
                "key_talking_points": [],
                "red_flags_to_address": [],
            }
        except Exception as exc:
            logger.exception("Interview prep generation failed: %s", exc)
            raise
