"""
Match Scoring Engine
Combines vector cosine similarity with LLM analysis to score
how well a resume matches a job description.
"""

import json
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.embeddings import cosine_similarity, generate_embedding
from app.core.llm import get_llm
from app.models.job_match import JobMatch

logger = logging.getLogger(__name__)


class MatchScorer:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.llm = get_llm()

    async def score_job(
        self,
        user_id: uuid.UUID,
        resume_id: uuid.UUID,
        job_id: uuid.UUID,
        provider: str | None = None,
    ) -> JobMatch:
        """
        Score a resume against a job description.
        1. Cosine similarity of embeddings → base score (0-100)
        2. LLM analysis → missing_skills, strengths, weaknesses
        3. Combined weighted score
        4. Save to job_matches table
        """
        from sqlalchemy import select
        from app.models.resume import Resume
        from app.models.job import Job

        # Load resume and job
        resume_result = await self.db.execute(
            select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
        )
        resume = resume_result.scalar_one_or_none()
        if not resume:
            raise ValueError(f"Resume {resume_id} not found for user {user_id}")

        job_result = await self.db.execute(select(Job).where(Job.id == job_id))
        job = job_result.scalar_one_or_none()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # --- Step 1: Cosine similarity ---
        resume_text = self._build_resume_text(resume)
        job_text = f"{job.title} {job.company} {job.description or ''} {job.requirements or ''}"

        resume_emb = await generate_embedding(resume_text)
        job_emb = await generate_embedding(job_text)
        cosine_score = cosine_similarity(resume_emb, job_emb)
        cosine_score_pct = round(cosine_score * 100, 2)

        # --- Step 2: LLM analysis ---
        llm_result = await self._llm_analyze(
            resume_data=resume.parsed_data or {},
            job_title=job.title,
            job_company=job.company,
            job_description=(job.description or "")[:3000],
            provider=provider,
        )

        # --- Step 3: Combined score ---
        # 40% cosine + 60% LLM skill match
        llm_score = llm_result.get("skill_match_score", cosine_score_pct)
        final_score = round(0.4 * cosine_score_pct + 0.6 * llm_score, 1)
        final_score = max(0.0, min(100.0, final_score))

        # --- Step 4: Upsert to DB ---
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        existing_result = await self.db.execute(
            select(JobMatch).where(
                JobMatch.user_id == user_id,
                JobMatch.job_id == job_id,
                JobMatch.resume_id == resume_id,
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing:
            existing.match_score = final_score
            existing.cosine_score = cosine_score_pct
            existing.missing_skills = llm_result.get("missing_skills", [])
            existing.strengths = llm_result.get("strengths", [])
            existing.weaknesses = llm_result.get("weaknesses", [])
            existing.summary = llm_result.get("summary", "")
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        else:
            match = JobMatch(
                user_id=user_id,
                job_id=job_id,
                resume_id=resume_id,
                match_score=final_score,
                cosine_score=cosine_score_pct,
                missing_skills=llm_result.get("missing_skills", []),
                strengths=llm_result.get("strengths", []),
                weaknesses=llm_result.get("weaknesses", []),
                summary=llm_result.get("summary", ""),
            )
            self.db.add(match)
            await self.db.flush()
            await self.db.refresh(match)
            return match

    def _build_resume_text(self, resume) -> str:
        if not resume.parsed_data:
            return resume.raw_text or ""
        d = resume.parsed_data
        parts = []
        if d.get("skills"):
            parts.append("Skills: " + ", ".join(d["skills"]))
        if d.get("experience"):
            for exp in d["experience"]:
                parts.append(f"{exp.get('title', '')} at {exp.get('company', '')}")
                if exp.get("description"):
                    parts.append(exp["description"])
        if d.get("education"):
            for edu in d["education"]:
                parts.append(f"{edu.get('degree', '')} {edu.get('institution', '')}")
        return "\n".join(parts)

    async def _llm_analyze(
        self,
        resume_data: dict,
        job_title: str,
        job_company: str,
        job_description: str,
        provider: str | None = None,
    ) -> dict:
        """LLM-powered skill gap analysis."""
        skills = resume_data.get("skills", [])
        exp_summary = []
        for exp in resume_data.get("experience", [])[:3]:
            exp_summary.append(f"{exp.get('title', '')} at {exp.get('company', '')}")

        system_prompt = """You are a job match analyst. Analyze the resume against the job description and return ONLY valid JSON:
{
  "skill_match_score": 75,
  "missing_skills": ["skill1", "skill2"],
  "strengths": ["relevant strength 1", "relevant strength 2"],
  "weaknesses": ["gap or weakness 1"],
  "summary": "One paragraph summary of the match quality"
}
skill_match_score: 0-100 integer based on skills overlap.
Be specific and actionable. Focus on skills and experience relevance."""

        user_prompt = f"""
Job: {job_title} at {job_company}

Job Description:
{job_description}

Candidate Skills: {', '.join(skills[:30])}
Candidate Experience: {'; '.join(exp_summary)}

Analyze the match and return JSON."""

        try:
            response = await self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                provider=provider,
                temperature=0.2,
                max_tokens=1024,
            )
            cleaned = response.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            return json.loads(cleaned)
        except Exception as exc:
            logger.warning("LLM match analysis failed: %s", exc)
            return {"skill_match_score": 50, "missing_skills": [], "strengths": [], "weaknesses": []}
