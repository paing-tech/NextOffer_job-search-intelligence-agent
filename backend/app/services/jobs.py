"""Job-link analysis: fetch (or accept pasted text) -> structured extraction -> persist.

Split into a network/LLM-only step (``fetch_and_extract``, no session — safe to
run concurrently) and a DB step (``persist_posting``), so the Gmail scan
pipeline can fetch a job link found in an email during its concurrent batch
and only touch the database afterwards, in its sequential write phase.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import JobPosting
from app.integrations.jobfetch import detect_platform, fetch_posting
from app.llm.extraction import extract_job_posting
from app.llm.schemas import JobPostingExtraction

_settings = get_settings()


@dataclass
class JobFetchResult:
    extraction: JobPostingExtraction
    platform: str
    raw_text: str
    source_url: str | None
    usage: dict
    fetch_source: str | None = None


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


async def fetch_and_extract(url: str) -> JobFetchResult | dict:
    """Network + LLM only, no DB. Returns a dict like ``{"status": "needs_paste", ...}``
    if the page couldn't be read automatically."""
    fetched = await fetch_posting(url)
    if fetched.needs_paste:
        return {
            "status": "needs_paste",
            "platform": fetched.platform,
            "reason": fetched.reason,
            "message": (
                f"I couldn't read that {fetched.platform} posting automatically. "
                "Paste the job description text and I'll summarize it."
            ),
        }
    extraction, usage = await extract_job_posting(fetched.text, fetched.final_url or url)
    return JobFetchResult(
        extraction=extraction,
        platform=fetched.platform,
        raw_text=fetched.text,
        source_url=fetched.final_url or url,
        usage=usage,
        fetch_source=fetched.source,
    )


def persist_posting(session: AsyncSession, *, user_id: uuid.UUID, result: JobFetchResult) -> JobPosting:
    posting = JobPosting(
        user_id=user_id,
        source_url=result.source_url,
        source_platform=result.platform,
        raw_text=result.raw_text[:40000],
        company=result.extraction.company,
        title=result.extraction.title,
        location=result.extraction.location,
        employment_type=result.extraction.employment_type,
        seniority=result.extraction.seniority,
        remote_policy=result.extraction.remote_policy,
        salary_text=result.extraction.salary_text,
        skills=result.extraction.skills,
        experience_requirements=result.extraction.experience_requirements,
        education_requirements=result.extraction.education_requirements,
        summary=result.extraction.summary,
        model=_settings.foundry_deployment,
        token_usage=result.usage,
    )
    session.add(posting)
    return posting


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

    if text:
        extraction, usage = await extract_job_posting(text, url)
        result = JobFetchResult(
            extraction=extraction,
            platform=detect_platform(url) if url else "manual",
            raw_text=text,
            source_url=url,
            usage=usage,
            fetch_source="pasted-text",
        )
    else:
        outcome = await fetch_and_extract(url)  # type: ignore[arg-type]
        if isinstance(outcome, dict):
            return outcome
        result = outcome

    posting = persist_posting(session, user_id=user_id, result=result)
    await session.flush()

    return {"status": "ok", "job_posting": serialize_posting(posting), "fetch_source": result.fetch_source}
