import pytest
from sqlalchemy import select

from app.db.models import JobPosting
from app.integrations.jobfetch import FetchResult
from app.llm.schemas import JobPostingExtraction
from app.services import jobs as jobs_service


@pytest.fixture
def fake_extraction(monkeypatch):
    async def _fake(text, source_url=None):
        return (
            JobPostingExtraction(
                company="Acme",
                title="Backend Engineer",
                skills=["Python", "FastAPI"],
                experience_requirements=["2+ years backend experience"],
            ),
            {"total_tokens": 100},
        )

    monkeypatch.setattr(jobs_service, "extract_job_posting", _fake)


async def test_analyze_job_from_text_persists_posting(session, user, fake_extraction):
    result = await jobs_service.analyze_job(session, user_id=user.id, text="Long JD text " * 50)
    assert result["status"] == "ok"
    assert result["job_posting"]["company"] == "Acme"
    assert result["job_posting"]["skills"] == ["Python", "FastAPI"]

    rows = (await session.scalars(select(JobPosting).where(JobPosting.user_id == user.id))).all()
    assert len(rows) == 1


async def test_analyze_job_needs_paste_when_fetch_walled(session, user, monkeypatch, fake_extraction):
    async def _walled(url, **kw):
        return FetchResult("linkedin", "", needs_paste=True, reason="login wall")

    monkeypatch.setattr(jobs_service, "fetch_posting", _walled)
    result = await jobs_service.analyze_job(session, user_id=user.id, url="https://linkedin.com/jobs/view/1")
    assert result["status"] == "needs_paste"
    assert result["platform"] == "linkedin"
    assert (await session.scalars(select(JobPosting))).all() == []
