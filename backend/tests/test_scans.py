from datetime import date

from sqlalchemy import select

from app.db.models import Application, ApplicationStatus, ProcessedEmail
from app.integrations.gmail import GmailError
from app.llm.schemas import EmailClassification
from app.services import scans


def _async_return(value):
    async def _fn(*args, **kwargs):
        return value

    return _fn


def _patch_access_token(monkeypatch, token="token"):
    monkeypatch.setattr(scans, "get_valid_access_token", _async_return(token))


async def test_run_scan_creates_application_from_job_related_email(session, user, monkeypatch):
    _patch_access_token(monkeypatch)
    monkeypatch.setattr(scans, "list_message_ids", _async_return(["m1"]))

    classification = EmailClassification(
        job_related=True,
        event_type="interview",
        company="Acme",
        job_title="Backend Engineer",
        next_action="Prepare for the call",
        next_action_due="2026-02-01",
        summary="Interview scheduled.",
    )

    async def fake_fetch_and_classify(access_token, message_id):
        return message_id, None, classification, None

    monkeypatch.setattr(scans, "_fetch_and_classify", fake_fetch_and_classify)

    run = await scans.run_scan(session, user_id=user.id, start_date=date(2026, 1, 1), end_date=None)

    assert run.status == "completed"
    assert run.messages_scanned == 1
    assert run.events_created == 1
    app = list(await session.scalars(select(Application)))[0]
    assert app.company == "Acme"
    assert app.status == ApplicationStatus.interview

    processed = list(await session.scalars(select(ProcessedEmail)))
    assert len(processed) == 1
    assert processed[0].classification == "job_related"
    assert processed[0].application_id == app.id


async def test_run_scan_skips_already_processed_messages(session, user, monkeypatch):
    session.add(ProcessedEmail(user_id=user.id, gmail_message_id="seen", classification="not_related"))
    await session.flush()

    _patch_access_token(monkeypatch)
    monkeypatch.setattr(scans, "list_message_ids", _async_return(["seen"]))

    called = []

    async def fake_fetch_and_classify(access_token, message_id):
        called.append(message_id)
        return message_id, None, None, None

    monkeypatch.setattr(scans, "_fetch_and_classify", fake_fetch_and_classify)

    run = await scans.run_scan(session, user_id=user.id, start_date=date(2026, 1, 1), end_date=None)
    assert called == []  # never re-fetched
    assert run.messages_scanned == 0


async def test_run_scan_records_not_related_without_creating_application(session, user, monkeypatch):
    _patch_access_token(monkeypatch)
    monkeypatch.setattr(scans, "list_message_ids", _async_return(["m2"]))

    classification = EmailClassification(job_related=False)

    async def fake_fetch_and_classify(access_token, message_id):
        return message_id, None, classification, None

    monkeypatch.setattr(scans, "_fetch_and_classify", fake_fetch_and_classify)

    run = await scans.run_scan(session, user_id=user.id, start_date=date(2026, 1, 1), end_date=None)
    assert run.events_created == 0
    processed = list(await session.scalars(select(ProcessedEmail)))
    assert processed[0].classification == "not_related"
    assert processed[0].application_id is None


async def test_run_scan_records_error_without_crashing(session, user, monkeypatch):
    _patch_access_token(monkeypatch)
    monkeypatch.setattr(scans, "list_message_ids", _async_return(["m3"]))

    async def fake_fetch_and_classify(access_token, message_id):
        return message_id, None, None, RuntimeError("boom")

    monkeypatch.setattr(scans, "_fetch_and_classify", fake_fetch_and_classify)

    run = await scans.run_scan(session, user_id=user.id, start_date=date(2026, 1, 1), end_date=None)
    assert run.status == "completed"
    assert run.messages_scanned == 1
    processed = list(await session.scalars(select(ProcessedEmail)))
    assert processed[0].classification == "error"


async def test_run_scan_marks_failed_on_gmail_error(session, user, monkeypatch):
    _patch_access_token(monkeypatch)

    async def raise_error(*args, **kwargs):
        raise GmailError("quota exceeded")

    monkeypatch.setattr(scans, "list_message_ids", raise_error)

    run = await scans.run_scan(session, user_id=user.id, start_date=date(2026, 1, 1), end_date=None)
    assert run.status == "failed"
    assert "quota exceeded" in run.error
