"""Information extraction over free text using structured LLM output."""

from __future__ import annotations

from app.llm.client import complete
from app.llm.schemas import EmailClassification, JobPostingExtraction, strict_schema

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


_EMAIL_SYSTEM = (
    "You classify one email for a job-search tracker. Decide if it concerns a specific job "
    "application of the recipient's — not a job board digest, newsletter, or unrelated mail.\n\n"
    "If job_related: pick event_type — 'applied' (application confirmation), 'assessment' "
    "(test/task request), 'interview' (interview scheduling or invite), 'rejection', 'offer', "
    "'status_update' (any other concrete progress signal), or 'other' (job-related but no clear "
    "status signal, e.g. a recruiter follow-up). Extract company and job_title exactly as named. "
    "job_url is the link to the job posting page itself, if the email includes one — typically a "
    "'view job' or job-title link, often shown in the text as 'label (https://...)'. It must be a "
    "page a person would browse, ending in something like a job ID or slug (e.g. '/job/12345' or "
    "'/jobs/view/...'). Never pick a logo, icon, tracking-pixel, unsubscribe, or preferences link — "
    "those usually end in an image extension (.png/.gif/.jpg) or contain words like 'track', "
    "'pixel', 'logo', 'icon', 'unsubscribe'. If no genuine job-posting link is present, use null — "
    "never guess or reuse an unrelated URL from the email. next_action is a short actionable step for the "
    "candidate, else null. next_action_due is an ISO date only if a specific deadline/date is stated, "
    "else null. summary is one plain sentence.\n\n"
    "If not job_related, set job_related to false and leave every other field null."
)


async def classify_email(*, subject: str, sender: str, date: str, body_text: str) -> tuple[EmailClassification, dict]:
    user = f"From: {sender}\nDate: {date}\nSubject: {subject}\n\n{body_text}"
    result = await complete(
        messages=[
            {"role": "system", "content": _EMAIL_SYSTEM},
            {"role": "user", "content": user[:16000]},
        ],
        response_schema=strict_schema(EmailClassification),
        max_tokens=1500,
    )
    if result.parsed is None:
        raise ValueError("Model did not return valid structured output for the email.")
    return EmailClassification.model_validate(result.parsed), result.usage
