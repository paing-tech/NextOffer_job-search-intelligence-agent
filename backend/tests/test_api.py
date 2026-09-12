"""End-to-end wiring test: real ASGI app, SQLite session, real minted JWT."""

import uuid

import jwt
import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models import Base
from app.db.session import get_session
from app.integrations import google_oauth
from app.main import app

SECRET = get_settings().auth_secret


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def _override():
        async with maker() as s:
            yield s
            await s.commit()

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
    await engine.dispose()


def _token(user_id: str, email: str) -> str:
    return jwt.encode({"sub": user_id, "email": email}, SECRET, algorithm="HS256")


@pytest.mark.asyncio
async def test_health(client):
    assert (await client.get("/health")).json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register_login_and_authed_route(client):
    reg = await client.post("/auth/register", json={"email": "Me@Example.com", "password": "hunter2hunter2"})
    assert reg.status_code == 201
    user_id = reg.json()["id"]

    dup = await client.post("/auth/register", json={"email": "me@example.com", "password": "hunter2hunter2"})
    assert dup.status_code == 409

    login = await client.post("/auth/login", json={"email": "me@example.com", "password": "hunter2hunter2"})
    assert login.status_code == 200
    assert login.json()["id"] == user_id

    bad = await client.post("/auth/login", json={"email": "me@example.com", "password": "wrongwrong"})
    assert bad.status_code == 401

    unauth = await client.get("/applications")
    assert unauth.status_code == 401

    authed = await client.get(
        "/applications", headers={"Authorization": f"Bearer {_token(user_id, 'me@example.com')}"}
    )
    assert authed.status_code == 200
    assert authed.json() == {"applications": []}


@pytest.mark.asyncio
async def test_check_email_states(client):
    fresh = await client.post("/auth/exists", json={"email": "new@example.com"})
    assert fresh.json() == {"exists": False, "has_password": False}

    await client.post("/auth/register", json={"email": "pw@example.com", "password": "hunter2hunter2"})
    with_pw = await client.post("/auth/exists", json={"email": "PW@example.com"})
    assert with_pw.json() == {"exists": True, "has_password": True}

    await client.post("/auth/oauth-upsert", json={"email": "google-only@example.com"})
    google_only = await client.post("/auth/exists", json={"email": "google-only@example.com"})
    assert google_only.json() == {"exists": True, "has_password": False}


@pytest.mark.asyncio
async def test_oauth_upsert_creates_then_converges(client):
    first = await client.post("/auth/oauth-upsert", json={"email": "Google@Example.com"})
    assert first.status_code == 200
    user_id = first.json()["id"]

    again = await client.post("/auth/oauth-upsert", json={"email": "google@example.com"})
    assert again.json()["id"] == user_id  # same email -> same account, no duplicate

    # A pre-existing password account with the same email resolves to that same user.
    reg = await client.post("/auth/register", json={"email": "both@example.com", "password": "hunter2hunter2"})
    via_oauth = await client.post("/auth/oauth-upsert", json={"email": "both@example.com"})
    assert via_oauth.json()["id"] == reg.json()["id"]


@pytest.mark.asyncio
async def test_create_application_endpoint(client):
    reg = await client.post("/auth/register", json={"email": "a@example.com", "password": "hunter2hunter2"})
    token = _token(reg.json()["id"], "a@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    made = await client.post(
        "/applications", json={"company": "Acme", "job_title": "Backend Engineer", "status": "applied"}, headers=headers
    )
    assert made.status_code == 201
    assert made.json()["created"] is True

    again = await client.post(
        "/applications", json={"company": "acme", "job_title": "backend engineer", "status": "interview"}, headers=headers
    )
    assert again.json()["created"] is False
    assert again.json()["application"]["status"] == "interview"

    listed = await client.get("/applications", headers=headers)
    assert len(listed.json()["applications"]) == 1


@pytest.mark.asyncio
async def test_get_application_includes_linked_job_posting(client, monkeypatch):
    from app.llm.schemas import JobPostingExtraction
    from app.services import jobs as jobs_service

    async def fake_extract(text, source_url=None):
        return (
            JobPostingExtraction(company="Acme", title="Backend Engineer", skills=["Python", "FastAPI"], summary="Build things."),
            {},
        )

    monkeypatch.setattr(jobs_service, "extract_job_posting", fake_extract)

    reg = await client.post("/auth/register", json={"email": "b@example.com", "password": "hunter2hunter2"})
    headers = {"Authorization": f"Bearer {_token(reg.json()['id'], 'b@example.com')}"}

    analyzed = await client.post("/jobs/analyze", json={"text": "a" * 60}, headers=headers)
    posting_id = analyzed.json()["job_posting"]["id"]

    made = await client.post(
        "/applications",
        json={"company": "Acme", "job_title": "Backend Engineer", "job_posting_id": posting_id},
        headers=headers,
    )
    app_id = made.json()["application"]["id"]

    detail = await client.get(f"/applications/{app_id}", headers=headers)
    assert detail.json()["job_posting"]["summary"] == "Build things."
    assert detail.json()["job_posting"]["skills"] == ["Python", "FastAPI"]


@pytest.mark.asyncio
async def test_google_status_not_connected(client):
    reg = await client.post("/auth/register", json={"email": "g1@example.com", "password": "hunter2hunter2"})
    token = _token(reg.json()["id"], "g1@example.com")
    resp = await client.get("/google/status", headers={"Authorization": f"Bearer {token}"})
    assert resp.json() == {"connected": False}


@pytest.mark.asyncio
async def test_google_authorize_redirects_to_google(client):
    reg = await client.post("/auth/register", json={"email": "g2@example.com", "password": "hunter2hunter2"})
    state = _token(reg.json()["id"], "g2@example.com")
    resp = await client.get(f"/google/authorize?state={state}", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert resp.headers["location"].startswith("https://accounts.google.com/o/oauth2/v2/auth")
    assert "gmail.readonly" in resp.headers["location"]


@pytest.mark.asyncio
async def test_google_authorize_rejects_bad_state(client):
    resp = await client.get("/google/authorize?state=garbage", follow_redirects=False)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_google_callback_missing_code_redirects_with_error(client):
    resp = await client.get("/google/callback", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "google=error" in resp.headers["location"]


@pytest.mark.asyncio
async def test_google_callback_success_then_disconnect(client, monkeypatch):
    from app.routers import google as google_router

    monkeypatch.setattr(google_oauth._settings, "token_encryption_key", Fernet.generate_key().decode())
    google_oauth._fernet.cache_clear()

    reg = await client.post("/auth/register", json={"email": "g3@example.com", "password": "hunter2hunter2"})
    state = _token(reg.json()["id"], "g3@example.com")
    headers = {"Authorization": f"Bearer {state}"}

    async def fake_exchange(code):
        assert code == "abc"
        return {"access_token": "a1", "refresh_token": "r1", "expires_in": 3600, "scope": "x"}

    monkeypatch.setattr(google_router, "exchange_code", fake_exchange)

    callback = await client.get(f"/google/callback?code=abc&state={state}", follow_redirects=False)
    assert callback.status_code in (302, 307)
    assert "google=connected" in callback.headers["location"]

    status = await client.get("/google/status", headers=headers)
    assert status.json()["connected"] is True

    disconnected = await client.delete("/google/connection", headers=headers)
    assert disconnected.json() == {"connected": False}
    status_after = await client.get("/google/status", headers=headers)
    assert status_after.json() == {"connected": False}

    google_oauth._fernet.cache_clear()


@pytest.mark.asyncio
async def test_create_spreadsheet_requires_connection(client):
    reg = await client.post("/auth/register", json={"email": "sheet1@example.com", "password": "hunter2hunter2"})
    token = _token(reg.json()["id"], "sheet1@example.com")
    resp = await client.post("/google/spreadsheet", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_spreadsheet_after_connecting(client, monkeypatch):
    from app.routers import google as google_router

    monkeypatch.setattr(google_oauth._settings, "token_encryption_key", Fernet.generate_key().decode())
    google_oauth._fernet.cache_clear()

    reg = await client.post("/auth/register", json={"email": "sheet2@example.com", "password": "hunter2hunter2"})
    state = _token(reg.json()["id"], "sheet2@example.com")
    headers = {"Authorization": f"Bearer {state}"}

    async def fake_exchange(code):
        return {"access_token": "a1", "refresh_token": "r1", "expires_in": 3600, "scope": "x"}

    monkeypatch.setattr(google_router, "exchange_code", fake_exchange)
    await client.get(f"/google/callback?code=abc&state={state}", follow_redirects=False)

    async def fake_create(access_token):
        assert access_token == "a1"
        return {"id": "sheet123", "url": "https://docs.google.com/spreadsheets/d/sheet123/edit"}

    monkeypatch.setattr(google_router, "create_tracker_spreadsheet", fake_create)
    resp = await client.post("/google/spreadsheet", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {
        "spreadsheet_id": "sheet123",
        "url": "https://docs.google.com/spreadsheets/d/sheet123/edit",
        "resynced": 0,
    }

    status_resp = await client.get("/google/status", headers=headers)
    assert status_resp.json()["spreadsheet_id"] == "sheet123"
    assert status_resp.json()["spreadsheet_url"] == "https://docs.google.com/spreadsheets/d/sheet123/edit"

    google_oauth._fernet.cache_clear()


@pytest.mark.asyncio
async def test_scan_run_requires_google_connection(client):
    reg = await client.post("/auth/register", json={"email": "s@example.com", "password": "hunter2hunter2"})
    token = _token(reg.json()["id"], "s@example.com")
    resp = await client.post(
        "/scans/run", json={"start_date": "2026-01-01"}, headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_scan_run_rejects_bad_date_range(client):
    reg = await client.post("/auth/register", json={"email": "s2@example.com", "password": "hunter2hunter2"})
    token = _token(reg.json()["id"], "s2@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post(
        "/scans/run", json={"start_date": "2026-01-10", "end_date": "2026-01-01"}, headers=headers
    )
    assert resp.status_code == 422
