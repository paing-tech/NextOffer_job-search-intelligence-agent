from datetime import date

from sqlalchemy import select

from app.db.models import ProcessedEmail
from app.llm.schemas import EmailClassification
from app.services import scans


def _async_return(value):
    async def _fn(*args, **kwargs):
        return value

    return _fn


async def test_force_rescans_and_updates_existing_row_in_place(session, user, monkeypatch):
    session.add(ProcessedEmail(user_id=user.id, gmail_message_id="m1", classification="error"))
    await session.flush()

    monkeypatch.setattr(scans, "get_valid_access_token", _async_return("token"))
    monkeypatch.setattr(scans, "list_message_ids", _async_return(["m1"]))

    classification = EmailClassification(job_related=True, event_type="applied", company="Acme", job_title="BE")

    async def fake_fetch_and_classify(access_token, message_id):
        return message_id, None, classification, None, None

    monkeypatch.setattr(scans, "_fetch_and_classify", fake_fetch_and_classify)

    run = await scans.run_scan(session, user_id=user.id, start_date=date(2026, 1, 1), end_date=None, force=True)

    assert run.messages_scanned == 1
    assert run.events_created == 1
    rows = list(await session.scalars(select(ProcessedEmail).where(ProcessedEmail.user_id == user.id)))
    assert len(rows) == 1  # updated in place, not duplicated
    assert rows[0].classification == "job_related"


async def test_without_force_already_seen_messages_are_skipped(session, user, monkeypatch):
    session.add(ProcessedEmail(user_id=user.id, gmail_message_id="m1", classification="error"))
    await session.flush()

    monkeypatch.setattr(scans, "get_valid_access_token", _async_return("token"))
    monkeypatch.setattr(scans, "list_message_ids", _async_return(["m1"]))

    called = []

    async def fake_fetch_and_classify(access_token, message_id):
        called.append(message_id)
        return message_id, None, None, None, None

    monkeypatch.setattr(scans, "_fetch_and_classify", fake_fetch_and_classify)

    run = await scans.run_scan(session, user_id=user.id, start_date=date(2026, 1, 1), end_date=None)
    assert called == []
    assert run.messages_scanned == 0
