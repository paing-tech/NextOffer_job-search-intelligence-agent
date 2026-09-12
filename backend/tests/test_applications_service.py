from sqlalchemy import select

from app.db.models import ApplicationEvent, ApplicationStatus
from app.services.applications import dedupe_key, search_applications, upsert_application


def test_dedupe_key_normalizes():
    assert dedupe_key("Acme, Inc.", "Backend  Engineer") == dedupe_key("acme inc", "backend engineer")


async def test_upsert_creates_then_updates(session, user):
    app, created = await upsert_application(
        session, user_id=user.id, company="Acme", job_title="Backend Engineer", status=ApplicationStatus.applied
    )
    assert created is True

    same, created2 = await upsert_application(
        session, user_id=user.id, company="acme", job_title="backend engineer", status=ApplicationStatus.interview
    )
    assert created2 is False
    assert same.id == app.id
    assert same.status == ApplicationStatus.interview


async def test_status_does_not_regress(session, user):
    await upsert_application(
        session, user_id=user.id, company="Acme", job_title="BE", status=ApplicationStatus.interview
    )
    app, _ = await upsert_application(
        session, user_id=user.id, company="Acme", job_title="BE", status=ApplicationStatus.applied
    )
    assert app.status == ApplicationStatus.interview


async def test_search_by_query(session, user):
    await upsert_application(session, user_id=user.id, company="Acme", job_title="Backend Engineer")
    await upsert_application(session, user_id=user.id, company="Globex", job_title="Data Scientist")
    results = await search_applications(session, user_id=user.id, query="globex")
    assert [r.company for r in results] == ["Globex"]


async def test_status_changed_at_set_on_creation(session, user):
    app, _ = await upsert_application(
        session, user_id=user.id, company="Acme", job_title="BE", status=ApplicationStatus.applied
    )
    assert app.status_changed_at is not None


async def test_status_changed_at_updates_only_on_real_transition(session, user):
    app, _ = await upsert_application(
        session, user_id=user.id, company="Acme", job_title="BE", status=ApplicationStatus.applied
    )
    first_changed_at = app.status_changed_at

    # Unrelated field edit, same status: status_changed_at must not move.
    app, _ = await upsert_application(
        session, user_id=user.id, company="Acme", job_title="BE", next_action="Follow up"
    )
    assert app.status_changed_at == first_changed_at
    assert app.next_action == "Follow up"

    # Actual status transition: status_changed_at must advance.
    app, _ = await upsert_application(
        session, user_id=user.id, company="Acme", job_title="BE", status=ApplicationStatus.interview
    )
    assert app.status_changed_at is not None
    assert app.status_changed_at >= first_changed_at


async def test_status_transition_without_explicit_event_is_auto_logged(session, user):
    app, _ = await upsert_application(
        session, user_id=user.id, company="Acme", job_title="BE", status=ApplicationStatus.applied
    )
    await upsert_application(
        session, user_id=user.id, company="Acme", job_title="BE", status=ApplicationStatus.interview
    )
    events = list(
        await session.scalars(select(ApplicationEvent).where(ApplicationEvent.application_id == app.id))
    )
    assert len(events) == 1
    assert "Interview" in events[0].summary


async def test_no_duplicate_event_when_status_unchanged(session, user):
    app, _ = await upsert_application(
        session, user_id=user.id, company="Acme", job_title="BE", status=ApplicationStatus.applied
    )
    await upsert_application(session, user_id=user.id, company="Acme", job_title="BE", next_action="Follow up")
    events = list(
        await session.scalars(select(ApplicationEvent).where(ApplicationEvent.application_id == app.id))
    )
    assert len(events) == 0
