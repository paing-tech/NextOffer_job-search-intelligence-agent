"""Manual Gmail scan trigger, date-range bounded (a scheduled version — running
this automatically in the background — is milestone 3)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.models import ScanRun, User
from app.db.session import get_session
from app.integrations.google_oauth import GoogleNotConnected, GoogleOAuthError
from app.services.auto_scan import get_auto_scan_config, serialize_auto_scan_config, set_auto_scan_config
from app.services.scans import run_scan, serialize_scan_run

router = APIRouter(prefix="/scans", tags=["scans"])


class ScanRequest(BaseModel):
    start_date: date
    end_date: date | None = None  # None = up to now
    force: bool = False  # rescan messages already seen in a prior run

    @model_validator(mode="after")
    def _range_is_sane(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if self.start_date > date.today():
            raise ValueError("start_date can't be in the future")
        return self


@router.get("")
async def list_scans(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> dict:
    runs = list(
        await session.scalars(
            select(ScanRun).where(ScanRun.user_id == user.id).order_by(ScanRun.started_at.desc()).limit(20)
        )
    )
    return {"scans": [serialize_scan_run(r) for r in runs]}


@router.post("/run")
async def run_scan_endpoint(
    body: ScanRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        run = await run_scan(
            session, user_id=user.id, start_date=body.start_date, end_date=body.end_date, force=body.force
        )
    except GoogleNotConnected as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Connect Google in Settings first.") from exc
    except GoogleOAuthError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    return serialize_scan_run(run)


class AutoScanRequest(BaseModel):
    enabled: bool
    start_date: date
    frequency_minutes: int = Field(default=30, ge=15, le=1440)

    @model_validator(mode="after")
    def _start_not_future(self):
        if self.start_date > date.today():
            raise ValueError("start_date can't be in the future")
        return self


@router.get("/auto")
async def get_auto_scan_endpoint(
    user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)
) -> dict:
    config = await get_auto_scan_config(session, user_id=user.id)
    return {"config": serialize_auto_scan_config(config) if config else None}


@router.put("/auto")
async def set_auto_scan_endpoint(
    body: AutoScanRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    config = await set_auto_scan_config(
        session,
        user_id=user.id,
        enabled=body.enabled,
        start_date=body.start_date,
        frequency_minutes=body.frequency_minutes,
    )
    return {"config": serialize_auto_scan_config(config)}
