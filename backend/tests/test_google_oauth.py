from datetime import datetime, timedelta, timezone

import pytest
from cryptography.fernet import Fernet

from app.db.models import GoogleConnection
from app.integrations import google_oauth


@pytest.fixture(autouse=True)
def _fernet_key(monkeypatch):
    monkeypatch.setattr(google_oauth._settings, "token_encryption_key", Fernet.generate_key().decode())
    google_oauth._fernet.cache_clear()
    yield
    google_oauth._fernet.cache_clear()


def test_encrypt_decrypt_roundtrip():
    enc = google_oauth.encrypt_token("refresh-value")
    assert enc != "refresh-value"
    assert google_oauth.decrypt_token(enc) == "refresh-value"


async def test_save_connection_creates_row(session, user):
    await google_oauth.save_connection(
        session,
        user_id=user.id,
        tokens={"access_token": "a1", "refresh_token": "r1", "expires_in": 3600, "scope": "x"},
    )
    conn = await session.get(GoogleConnection, user.id)
    assert conn is not None
    assert google_oauth.decrypt_token(conn.encrypted_refresh_token) == "r1"
    assert conn.access_token == "a1"


async def test_save_connection_without_refresh_token_requires_existing_row(session, user):
    with pytest.raises(google_oauth.GoogleOAuthError):
        await google_oauth.save_connection(
            session, user_id=user.id, tokens={"access_token": "a1", "expires_in": 3600}
        )


async def test_get_valid_access_token_uses_cache(session, user):
    await google_oauth.save_connection(
        session,
        user_id=user.id,
        tokens={"access_token": "cached", "refresh_token": "r1", "expires_in": 3600},
    )
    assert await google_oauth.get_valid_access_token(session, user.id) == "cached"


async def test_get_valid_access_token_refreshes_when_expired(session, user, monkeypatch):
    conn = GoogleConnection(
        user_id=user.id,
        encrypted_refresh_token=google_oauth.encrypt_token("r1"),
        access_token="stale",
        token_expiry=datetime.now(timezone.utc) - timedelta(seconds=5),
    )
    session.add(conn)
    await session.flush()

    async def fake_refresh(refresh_token):
        assert refresh_token == "r1"
        return {"access_token": "fresh", "expires_in": 3600}

    monkeypatch.setattr(google_oauth, "_refresh", fake_refresh)
    assert await google_oauth.get_valid_access_token(session, user.id) == "fresh"


async def test_get_valid_access_token_no_connection_raises(session, user):
    with pytest.raises(google_oauth.GoogleNotConnected):
        await google_oauth.get_valid_access_token(session, user.id)
