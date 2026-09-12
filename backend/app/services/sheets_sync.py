"""Keep a tracked application's row in the user's Google Sheet up to date.

Best-effort by design: a Sheets hiccup (not connected, no spreadsheet chosen
yet, a transient API error) must never block tracking an application in our
own database — it just means the row isn't mirrored this time.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Application, GoogleConnection
from app.integrations.google_oauth import GoogleNotConnected, get_valid_access_token
from app.integrations.sheets import SheetsError, append_row, update_row


async def sync_application(session: AsyncSession, *, user_id: uuid.UUID, application: Application) -> None:
    conn = await session.get(GoogleConnection, user_id)
    if conn is None or not conn.spreadsheet_id:
        return

    row = [
        application.company,
        application.job_title,
        application.status.value,
        application.next_action or "",
        application.last_update_at.isoformat() if application.last_update_at else "",
        application.source.value,
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
