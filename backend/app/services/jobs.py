"""Job-link analysis: fetch (or accept pasted text) -> structured extraction -> persist."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import JobPosting
from app.integrations.jobfetch import detect_platform, fetch_posting
from app.llm.extraction import extract_job_posting

_settings = get_settings()


def serialize_posting(posting: JobPosting) -> dict:
    return {
        "id": str(posting.id),
        "source_url": posting.source_url,
        "source_platform": posting.source_platform,
        "company": posting.company,
        "title": posting.title,
        "location": posting.location,
        "employment_type": posting.employment_type,
        "seniority": posting.seniority,
        "remote_policy": posting.remote_policy,
        "salary_text": posting.salary_text,
        "skills": posting.skills,
        "experience_requirements": posting.experience_requirements,
        "education_requirements": posting.education_requirements,
        "summary": posting.summary,
    }


async def analyze_job(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    url: str | None = None,
    text: str | None = None,
) -> dict:
    """Returns ``{"status": "needs_paste", ...}`` or ``{"status": "ok", "job_posting": {...}}``."""
    if not url and not text:
        return {"status": "error", "message": "Provide a job URL or the pasted job description text."}

    source_url = url
    platform = detect_platform(url) if url else "manual"
    raw_text = text

    if not raw_text and url:
        fetched = await fetch_posting(url)
        platform = fetched.platform
        if fetched.needs_paste:
            return {
                "status": "needs_paste",
                "platform": platform,
                "reason": fetched.reason,
                "message": (
                    f"I couldn't read that {platform} posting automatically. "
                    "Paste the job description text and I'll summarize it."
                ),
            }
        raw_text = fetched.text
        source_url = fetched.final_url or url

    extraction, usage = await extract_job_posting(raw_text or "", source_url)

    posting = JobPosting(
        user_id=user_id,
        source_url=source_url,
        source_platform=platform,
        raw_text=(raw_text or "")[:40000],
        company=extraction.company,
        title=extraction.title,
        location=extraction.location,
        employment_type=extraction.employment_type,
        seniority=extraction.seniority,
        remote_policy=extraction.remote_policy,
        salary_text=extraction.salary_text,
        skills=extraction.skills,
        experience_requirements=extraction.experience_requirements,
        education_requirements=extraction.education_requirements,
        summary=extraction.summary,
        model=_settings.foundry_deployment,
        token_usage=usage,
    )
    session.add(posting)
    await session.flush()

    return {"status": "ok", "job_posting": serialize_posting(posting)}
