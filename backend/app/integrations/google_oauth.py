"""Google OAuth: authorization URL, code exchange, and access-token refresh.

Raw REST calls (httpx) rather than google-auth/googleapiclient — those are sync
libraries and this app is async end to end; a couple of well-documented HTTP
calls are simpler than bridging a blocking client into the event loop.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import GoogleConnection

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"

# Gmail read-only + Sheets read/write. Keep this list in sync with the scopes
# approved on the OAuth consent screen's Data Access page, or Google rejects
# the request while the app is in Testing mode.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]

_settings = get_settings()
_EXPIRY_BUFFER = timedelta(seconds=60)


class GoogleNotConnected(RuntimeError):
    pass


class GoogleOAuthError(RuntimeError):
    pass


def build_auth_url(state: str) -> str:
    params = {
        "client_id": _settings.google_client_id,
        "redirect_uri": _settings.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",  # required to get a refresh_token
        "prompt": "consent",  # force it even if they connected before
        "state": state,
        "include_granted_scopes": "true",
    }
    return f"{AUTH_URL}?{httpx.QueryParams(params)}"


async def exchange_code(code: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "client_id": _settings.google_client_id,
                "client_secret": _settings.google_client_secret,
                "code": code,
                "redirect_uri": _settings.google_oauth_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    if resp.status_code != 200:
        raise GoogleOAuthError(f"Code exchange failed: {resp.status_code} {resp.text}")
    return resp.json()


async def _refresh(refresh_token: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "client_id": _settings.google_client_id,
                "client_secret": _settings.google_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
    if resp.status_code != 200:
        raise GoogleOAuthError(f"Token refresh failed: {resp.status_code} {resp.text}")
    return resp.json()


@lru_cache
def _fernet() -> Fernet:
    if not _settings.token_encryption_key:
        raise RuntimeError(
            "TOKEN_ENCRYPTION_KEY is not set. Generate one: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    return Fernet(_settings.token_encryption_key.encode())


def encrypt_token(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    try:
        return _fernet().decrypt(encrypted.encode()).decode()
    except InvalidToken as exc:
        raise GoogleOAuthError("Stored Google token could not be decrypted.") from exc


@dataclass
class ConnectionStatus:
    connected: bool
    google_email: str | None = None
    connected_at: datetime | None = None
    spreadsheet_id: str | None = None


async def save_connection(session: AsyncSession, *, user_id: uuid.UUID, tokens: dict) -> None:
    refresh_token = tokens.get("refresh_token")
    conn = await session.get(GoogleConnection, user_id)
    if conn is None:
        if not refresh_token:
            # Google only returns refresh_token on first consent. If the user
            # revoked access in their Google account and reconnects, a stale
            # connection row wouldn't exist either, so this shouldn't happen
            # in practice with access_type=offline&prompt=consent — but guard.
            raise GoogleOAuthError("Google did not return a refresh token. Try reconnecting.")
        conn = GoogleConnection(user_id=user_id, encrypted_refresh_token=encrypt_token(refresh_token))
        session.add(conn)
    elif refresh_token:
        conn.encrypted_refresh_token = encrypt_token(refresh_token)

    conn.access_token = tokens.get("access_token")
    expires_in = tokens.get("expires_in")
    conn.token_expiry = (
        datetime.now(timezone.utc) + timedelta(seconds=int(expires_in)) if expires_in else None
    )
    conn.scopes = tokens.get("scope") or " ".join(SCOPES)
    await session.flush()


async def get_valid_access_token(session: AsyncSession, user_id: uuid.UUID) -> str:
    """Return a live access token, refreshing it first if it's expired or missing."""
    conn = await session.get(GoogleConnection, user_id)
    if conn is None or not conn.encrypted_refresh_token:
        raise GoogleNotConnected("No Google connection for this user.")

    # SQLite (used in tests) returns naive datetimes even for tz-aware columns;
    # Postgres returns aware ones. Normalize so the comparison always works.
    expiry = conn.token_expiry
    if expiry is not None and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    fresh = conn.access_token and expiry and expiry > datetime.now(timezone.utc) + _EXPIRY_BUFFER
    if fresh:
        return conn.access_token

    tokens = await _refresh(decrypt_token(conn.encrypted_refresh_token))
    conn.access_token = tokens["access_token"]
    expires_in = tokens.get("expires_in")
    conn.token_expiry = (
        datetime.now(timezone.utc) + timedelta(seconds=int(expires_in)) if expires_in else None
    )
    await session.flush()
    return conn.access_token
