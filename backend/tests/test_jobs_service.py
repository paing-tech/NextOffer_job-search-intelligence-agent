import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.db.models import Application, JobPosting
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


async def test_list_job_postings_empty(session, user):
    assert await jobs_service.list_job_postings(session, user_id=user.id) == []


async def test_list_job_postings_orders_newest_first(session, user, fake_extraction):
    r1 = await jobs_service.analyze_job(session, user_id=user.id, text="First JD " * 50)
    r2 = await jobs_service.analyze_job(session, user_id=user.id, text="Second JD " * 50)

    # Backdate explicitly rather than relying on real-clock ordering between
    # the two inserts, which could tie at whole-second timestamp resolution.
    p1 = await session.get(JobPosting, uuid.UUID(r1["job_posting"]["id"]))
    p2 = await session.get(JobPosting, uuid.UUID(r2["job_posting"]["id"]))
    p1.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    p2.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    await session.flush()

    postings = await jobs_service.list_job_postings(session, user_id=user.id)
    assert [p["id"] for p in postings] == [str(p2.id), str(p1.id)]
    assert postings[0]["tracked_application_id"] is None


async def test_list_job_postings_flags_tracked_posting(session, user, fake_extraction):
    result = await jobs_service.analyze_job(session, user_id=user.id, text="JD text " * 50)
    posting_id = uuid.UUID(result["job_posting"]["id"])

    app = Application(
        user_id=user.id,
        company="Acme",
        job_title="Backend Engineer",
        dedupe_key="acme::backend engineer",
        job_posting_id=posting_id,
    )
    session.add(app)
    await session.flush()

    postings = await jobs_service.list_job_postings(session, user_id=user.id)
    assert postings[0]["tracked_application_id"] == str(app.id)
