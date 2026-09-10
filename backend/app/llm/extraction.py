"""Information extraction over free text using structured LLM output."""

from __future__ import annotations

from app.llm.client import complete
from app.llm.schemas import JobPostingExtraction, strict_schema

_JOB_SYSTEM = (
    "You extract structured data from job postings for a job-search tracker. "
    "Return ONLY fields supported by the text — never invent a company, salary, or requirement. "
    "Normalize aggressively:\n"
    "  * skills: short tokens as written in industry usage — 'Python', 'FastAPI', 'PostgreSQL', 'AWS', "
    "'Docker'. Split lists. No sentences, no versions unless essential.\n"
    "  * experience_requirements: compact phrases — '2+ years backend experience', "
    "'production ML experience', 'REST API design'.\n"
    "  * education_requirements: compact phrases — \"Bachelor's in CS or equivalent\". Empty list if "
    "the posting does not mention education.\n"
    "If a field is not stated, use null (or an empty list)."
)


async def extract_job_posting(text: str, source_url: str | None = None) -> tuple[JobPostingExtraction, dict]:
    """Return the parsed posting plus token-usage metadata."""
    user = text if not source_url else f"Source URL: {source_url}\n\n{text}"
    result = await complete(
        messages=[
            {"role": "system", "content": _JOB_SYSTEM},
            {"role": "user", "content": user[:24000]},
        ],
        response_schema=strict_schema(JobPostingExtraction),
        max_tokens=1200,
    )
    if result.parsed is None:
        raise ValueError("Model did not return valid structured output for the job posting.")
    return JobPostingExtraction.model_validate(result.parsed), result.usage
