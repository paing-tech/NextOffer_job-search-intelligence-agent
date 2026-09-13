import uuid
from datetime import date, datetime, timedelta, timezone

from app.db.models import AutoScanConfig, User
from app.integrations.google_oauth import GoogleNotConnected
from app.services import auto_scan
from app.services import scans as scans_module


def _async_return(value):
    async def _fn(*args, **kwargs):
        return value

    return _fn


async def test_get_auto_scan_config_none_when_missing(session, user):
    assert await auto_scan.get_auto_scan_config(session, user_id=user.id) is None


async def test_set_auto_scan_config_creates_then_updates(session, user):
    config = await auto_scan.set_auto_scan_config(
        session, user_id=user.id, enabled=True, start_date=date(2026, 1, 1), frequency_minutes=30
    )
    assert config.enabled is True
    assert config.frequency_minutes == 30

    updated = await auto_scan.set_auto_scan_config(
        session, user_id=user.id, enabled=False, start_date=date(2026, 2, 1), frequency_minutes=60
    )
    assert updated.user_id == config.user_id
    assert updated.enabled is False
    assert updated.start_date == date(2026, 2, 1)
    assert updated.frequency_minutes == 60
    assert (await auto_scan.get_auto_scan_config(session, user_id=user.id)).frequency_minutes == 60


async def test_run_due_auto_scans_skips_disabled_and_not_yet_due(session, user, monkeypatch):
    session.add(
        AutoScanConfig(user_id=user.id, enabled=False, start_date=date(2026, 1, 1), frequency_minutes=30)
    )
    await session.flush()

    called = []

    async def fake_list_message_ids(*a, **kw):
        called.append(1)
        return []

    monkeypatch.setattr(scans_module, "get_valid_access_token", _async_return("token"))
    monkeypatch.setattr(scans_module, "list_message_ids", fake_list_message_ids)

    assert await auto_scan.run_due_auto_scans(session) == 0
    assert called == []


async def test_run_due_auto_scans_runs_when_never_run_before(session, user, monkeypatch):
    session.add(AutoScanConfig(user_id=user.id, enabled=True, start_date=date(2026, 1, 1), frequency_minutes=30))
    await session.flush()

    monkeypatch.setattr(scans_module, "get_valid_access_token", _async_return("token"))
    monkeypatch.setattr(scans_module, "list_message_ids", _async_return([]))

    ran = await auto_scan.run_due_auto_scans(session)
    assert ran == 1

    config = await auto_scan.get_auto_scan_config(session, user_id=user.id)
    assert config.last_run_at is not None
    assert config.last_status == "completed"


async def test_run_due_auto_scans_skips_when_interval_not_elapsed(session, user, monkeypatch):
    config = AutoScanConfig(
        user_id=user.id,
        enabled=True,
        start_date=date(2026, 1, 1),
        frequency_minutes=30,
        last_run_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    session.add(config)
    await session.flush()

    monkeypatch.setattr(scans_module, "get_valid_access_token", _async_return("token"))
    called = []

    async def fake_list_message_ids(*a, **kw):
        called.append(1)
        return []

    monkeypatch.setattr(scans_module, "list_message_ids", fake_list_message_ids)

    assert await auto_scan.run_due_auto_scans(session) == 0
    assert called == []


async def test_run_due_auto_scans_runs_once_interval_has_elapsed(session, user, monkeypatch):
    session.add(
        AutoScanConfig(
            user_id=user.id,
            enabled=True,
            start_date=date(2026, 1, 1),
            frequency_minutes=30,
            last_run_at=datetime.now(timezone.utc) - timedelta(minutes=31),
        )
    )
    await session.flush()

    monkeypatch.setattr(scans_module, "get_valid_access_token", _async_return("token"))
    monkeypatch.setattr(scans_module, "list_message_ids", _async_return([]))

    assert await auto_scan.run_due_auto_scans(session) == 1


async def test_run_due_auto_scans_isolates_one_users_google_not_connected(session, user, monkeypatch):
    other = User(id=uuid.uuid4(), email="other@example.com")
    session.add(other)
    session.add(AutoScanConfig(user_id=user.id, enabled=True, start_date=date(2026, 1, 1)))
    session.add(AutoScanConfig(user_id=other.id, enabled=True, start_date=date(2026, 1, 1)))
    await session.flush()

    async def flaky_token(session, uid):
        if uid == user.id:
            raise GoogleNotConnected("not connected")
        return "token"

    monkeypatch.setattr(scans_module, "get_valid_access_token", flaky_token)
    monkeypatch.setattr(scans_module, "list_message_ids", _async_return([]))

    ran = await auto_scan.run_due_auto_scans(session)
    assert ran == 2  # both attempted

    failed_config = await auto_scan.get_auto_scan_config(session, user_id=user.id)
    ok_config = await auto_scan.get_auto_scan_config(session, user_id=other.id)
    assert failed_config.last_status == "not_connected"
    assert failed_config.last_run_at is not None
    assert ok_config.last_status == "completed"


async def test_run_due_auto_scans_isolates_unexpected_exception(session, user, monkeypatch):
    session.add(AutoScanConfig(user_id=user.id, enabled=True, start_date=date(2026, 1, 1)))
    await session.flush()

    async def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(scans_module, "get_valid_access_token", boom)

    ran = await auto_scan.run_due_auto_scans(session)
    assert ran == 1
    config = await auto_scan.get_auto_scan_config(session, user_id=user.id)
    assert config.last_status == "error"
    assert config.last_run_at is not None
