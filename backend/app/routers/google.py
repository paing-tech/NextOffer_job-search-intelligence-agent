"""Google connection: OAuth authorize/callback, status, disconnect.

`/authorize` and `/callback` are hit by the browser's own navigation (a real
redirect chain through Google), not the BFF — there is no Authorization header
on those requests, so the signed `state` param carries the user id instead.
`/status` and `/connection` go through the normal authenticated BFF path.
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import decode_state_token, get_current_user
from app.config import get_settings
from app.db.models import GoogleConnection, User
from app.db.session import get_session
from app.integrations.google_oauth import (
    GoogleNotConnected,
    GoogleOAuthError,
    build_auth_url,
    exchange_code,
    get_valid_access_token,
    save_connection,
)
from app.integrations.sheets import SheetsError, create_tracker_spreadsheet

router = APIRouter(prefix="/google", tags=["google"])
_settings = get_settings()


@router.get("/status")
async def connection_status(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> dict:
    conn = await session.get(GoogleConnection, user.id)
    if conn is None:
        return {"connected": False}
    return {
        "connected": True,
        "spreadsheet_id": conn.spreadsheet_id,
        "spreadsheet_url": (
            f"https://docs.google.com/spreadsheets/d/{conn.spreadsheet_id}/edit" if conn.spreadsheet_id else None
        ),
        "connected_at": conn.connected_at.isoformat() if conn.connected_at else None,
    }


@router.post("/spreadsheet")
async def create_spreadsheet(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> dict:
    conn = await session.get(GoogleConnection, user.id)
    if conn is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Connect Google first.")
    try:
        access_token = await get_valid_access_token(session, user.id)
        result = await create_tracker_spreadsheet(access_token)
    except (GoogleNotConnected, SheetsError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    conn.spreadsheet_id = result["id"]
    await session.flush()
    return {"spreadsheet_id": result["id"], "url": result["url"]}


@router.get("/authorize")
async def authorize(state: str) -> RedirectResponse:
    # Fail fast on a malformed/expired state rather than sending the user all
    # the way through Google's consent screen first.
    decode_state_token(state)
    return RedirectResponse(build_auth_url(state))


@router.get("/callback")
async def callback(
    session: AsyncSession = Depends(get_session),
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    settings_url = f"{_settings.frontend_url}/settings"
    if error or not code or not state:
        return RedirectResponse(f"{settings_url}?google=error&reason={quote(error or 'missing_code')}")

    try:
        user_id = decode_state_token(state)
        tokens = await exchange_code(code)
        await save_connection(session, user_id=user_id, tokens=tokens)
        await session.commit()
    except (HTTPException, GoogleOAuthError) as exc:
        await session.rollback()
        reason = exc.detail if isinstance(exc, HTTPException) else str(exc)
        return RedirectResponse(f"{settings_url}?google=error&reason={quote(str(reason))}")

    return RedirectResponse(f"{settings_url}?google=connected")


@router.delete("/connection")
async def disconnect(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> dict:
    conn = await session.get(GoogleConnection, user.id)
    if conn is not None:
        await session.delete(conn)
    return {"connected": False}
