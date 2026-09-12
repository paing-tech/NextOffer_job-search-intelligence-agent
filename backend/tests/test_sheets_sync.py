from app.db.models import Application, ApplicationSource, ApplicationStatus, GoogleConnection
from app.services import sheets_sync


def _async_return(value):
    async def _fn(*args, **kwargs):
        return value

    return _fn


def _new_application(user_id):
    return Application(
        user_id=user_id,
        company="Acme",
        job_title="Backend Engineer",
        dedupe_key="acme::backend engineer",
        status=ApplicationStatus.applied,
        source=ApplicationSource.manual,
    )


async def test_sync_noop_without_connection(session, user):
    app = _new_application(user.id)
    session.add(app)
    await session.flush()
    await sheets_sync.sync_application(session, user_id=user.id, application=app)
    assert app.sheet_row is None


async def test_sync_noop_without_spreadsheet(session, user):
    session.add(GoogleConnection(user_id=user.id, encrypted_refresh_token="x"))
    app = _new_application(user.id)
    session.add(app)
    await session.flush()
    await sheets_sync.sync_application(session, user_id=user.id, application=app)
    assert app.sheet_row is None


async def test_sync_appends_new_row(session, user, monkeypatch):
    session.add(GoogleConnection(user_id=user.id, encrypted_refresh_token="x", spreadsheet_id="sheet1"))
    app = _new_application(user.id)
    app.salary = "$5,000/mo"
    app.requirements = "Python, FastAPI (2+ years)"
    app.platform = "linkedin"
    session.add(app)
    await session.flush()

    monkeypatch.setattr(sheets_sync, "get_valid_access_token", _async_return("token"))
    captured = {}

    async def fake_append(access_token, spreadsheet_id, row):
        assert access_token == "token"
        assert spreadsheet_id == "sheet1"
        captured["row"] = row
        return 7

    monkeypatch.setattr(sheets_sync, "append_row", fake_append)

    await sheets_sync.sync_application(session, user_id=user.id, application=app)
    assert app.sheet_row == 7
    # Column order must match integrations.sheets.HEADER_ROW.
    date, job_title, company, salary, requirements, status, platform, next_action, updated = captured["row"]
    assert job_title == "Backend Engineer"
    assert company == "Acme"
    assert salary == "$5,000/mo"
    assert requirements == "Python, FastAPI (2+ years)"
    assert status == "Applied"
    assert platform == "LinkedIn"


async def test_sync_updates_existing_row(session, user, monkeypatch):
    session.add(GoogleConnection(user_id=user.id, encrypted_refresh_token="x", spreadsheet_id="sheet1"))
    app = _new_application(user.id)
    app.sheet_row = 3
    session.add(app)
    await session.flush()

    monkeypatch.setattr(sheets_sync, "get_valid_access_token", _async_return("token"))
    called = {}

    async def fake_update(access_token, spreadsheet_id, row_number, row):
        called["row_number"] = row_number

    monkeypatch.setattr(sheets_sync, "update_row", fake_update)

    await sheets_sync.sync_application(session, user_id=user.id, application=app)
    assert called["row_number"] == 3
    assert app.sheet_row == 3  # unchanged, we updated in place rather than appending


async def test_sync_swallows_sheets_error(session, user, monkeypatch):
    session.add(GoogleConnection(user_id=user.id, encrypted_refresh_token="x", spreadsheet_id="sheet1"))
    app = _new_application(user.id)
    session.add(app)
    await session.flush()

    monkeypatch.setattr(sheets_sync, "get_valid_access_token", _async_return("token"))

    async def fake_append(*args, **kwargs):
        raise sheets_sync.SheetsError("boom")

    monkeypatch.setattr(sheets_sync, "append_row", fake_append)

    await sheets_sync.sync_application(session, user_id=user.id, application=app)  # must not raise
    assert app.sheet_row is None
