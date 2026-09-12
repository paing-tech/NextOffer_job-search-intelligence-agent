from app.db.models import Application, ApplicationSource, ApplicationStatus, GoogleConnection
from app.services import sheets_sync


def _async_return(value):
    async def _fn(*args, **kwargs):
        return value

    return _fn


async def test_resync_all_clears_old_row_and_reappends(session, user, monkeypatch):
    session.add(GoogleConnection(user_id=user.id, encrypted_refresh_token="x", spreadsheet_id="new-sheet"))
    app1 = Application(
        user_id=user.id, company="Acme", job_title="BE", dedupe_key="acme::be",
        status=ApplicationStatus.applied, source=ApplicationSource.manual, sheet_row=5,
    )
    app2 = Application(
        user_id=user.id, company="Globex", job_title="DS", dedupe_key="globex::ds",
        status=ApplicationStatus.saved, source=ApplicationSource.manual, sheet_row=9,
    )
    session.add_all([app1, app2])
    await session.flush()

    monkeypatch.setattr(sheets_sync, "get_valid_access_token", _async_return("token"))
    appended = []

    async def fake_append(access_token, spreadsheet_id, row):
        assert spreadsheet_id == "new-sheet"
        appended.append(row)
        return len(appended)

    monkeypatch.setattr(sheets_sync, "append_row", fake_append)

    count = await sheets_sync.resync_all(session, user_id=user.id)

    assert count == 2
    assert len(appended) == 2  # both re-appended fresh, not updated at their stale row numbers
    assert app1.sheet_row is not None and app2.sheet_row is not None
