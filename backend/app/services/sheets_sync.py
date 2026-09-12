"""Keep a tracked application's row in the user's Google Sheet up to date.

Best-effort by design: a Sheets hiccup (not connected, no spreadsheet chosen
yet, a transient API error) must never block tracking an application in our
own database — it just means the row isn't mirrored this time.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Application, GoogleConnection
from app.integrations.google_oauth import GoogleNotConnected, get_valid_access_token
from app.integrations.sheets import SheetsError, append_row, update_row
from app.services.formatting import format_applied_date, format_last_updated, platform_label, status_label


async def sync_application(session: AsyncSession, *, user_id: uuid.UUID, application: Application) -> None:
    conn = await session.get(GoogleConnection, user_id)
    if conn is None or not conn.spreadsheet_id:
        return

    # Column order must match integrations.sheets.HEADER_ROW.
    row = [
        format_applied_date(application.first_seen_at),
        application.job_title,
        application.company,
        application.salary or "",
        application.requirements or "",
        status_label(application.status),
        platform_label(application.platform),
        application.next_action or "",
        format_last_updated(application.last_update_at),
    ]
    try:
        access_token = await get_valid_access_token(session, user_id)
        if application.sheet_row:
            await update_row(access_token, conn.spreadsheet_id, application.sheet_row, row)
        else:
            application.sheet_row = await append_row(access_token, conn.spreadsheet_id, row)
            await session.flush()
    except (GoogleNotConnected, SheetsError):
        pass


async def resync_all(session: AsyncSession, *, user_id: uuid.UUID) -> int:
    """After switching to a brand-new spreadsheet: every application's sheet_row
    pointed at a row in the *old* sheet, so clear that first, then re-append
    every application into the new one. Returns how many were resynced.

    Resets and re-syncs one application at a time, with no flush in between the
    two steps: `last_update_at` has a server-side `onupdate`, so a flush that
    touches the row without also setting that column expires it — reading it
    afterward (inside sync_application, to build the sheet row) would then need
    an implicit lazy reload, which AsyncSession can't do outside an awaited call.
    """
    apps = list(await session.scalars(select(Application).where(Application.user_id == user_id)))
    for app in apps:
        app.sheet_row = None
        await session.flush()
        await session.refresh(app)  # re-fetch fully, async-safe, so no attribute is left expired
        await sync_application(session, user_id=user_id, application=app)
    return len(apps)
