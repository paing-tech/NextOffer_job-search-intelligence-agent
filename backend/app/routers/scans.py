"""Email-scan endpoints — stubbed until milestone 2 (Gmail scan pipeline)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.models import ScanRun, User
from app.db.session import get_session

router = APIRouter(prefix="/scans", tags=["scans"])


@router.get("")
async def list_scans(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> dict:
    runs = list(
        await session.scalars(
            select(ScanRun).where(ScanRun.user_id == user.id).order_by(ScanRun.started_at.desc()).limit(20)
        )
    )
    return {
        "scans": [
            {
                "id": str(r.id),
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "messages_scanned": r.messages_scanned,
                "events_created": r.events_created,
                "applications_updated": r.applications_updated,
            }
            for r in runs
        ]
    }


@router.post("/run")
async def run_scan(user: User = Depends(get_current_user)) -> dict:
    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED,
        "The Gmail scan pipeline lands in milestone 2 (needs a connected Google account).",
    )
