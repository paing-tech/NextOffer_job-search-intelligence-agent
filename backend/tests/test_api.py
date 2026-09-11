"""End-to-end wiring test: real ASGI app, SQLite session, real minted JWT."""

import uuid

import jwt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db.models import Base
from app.db.session import get_session
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
async def test_scan_run_is_stubbed(client):
    reg = await client.post("/auth/register", json={"email": "s@example.com", "password": "hunter2hunter2"})
    token = _token(reg.json()["id"], "s@example.com")
    resp = await client.post("/scans/run", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 501
