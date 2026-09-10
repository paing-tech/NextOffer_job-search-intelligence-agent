from app.db.models import ApplicationStatus
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
