"""Scheduled Gmail scanning: a background loop (started from app.main's
lifespan) that polls AutoScanConfig every `auto_scan_poll_seconds` and
re-runs the same run_scan() pipeline the manual "Scan now" button uses for
whichever users are due — always from their fixed start_date through now.
run_scan() is naturally idempotent (ProcessedEmail dedup), so re-running it
on a timer never reprocesses old messages; it only ever picks up new ones.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AutoScanConfig
from app.db.session import SessionLocal
from app.integrations.google_oauth import GoogleNotConnected, GoogleOAuthError
from app.services.scans import run_scan


def serialize_auto_scan_config(config: AutoScanConfig) -> dict:
    return {
        "enabled": config.enabled,
        "start_date": config.start_date.isoformat() if config.start_date else None,
        "frequency_minutes": config.frequency_minutes,
        "last_run_at": config.last_run_at.isoformat() if config.last_run_at else None,
        "last_status": config.last_status,
    }


async def get_auto_scan_config(session: AsyncSession, *, user_id: uuid.UUID) -> AutoScanConfig | None:
    return await session.get(AutoScanConfig, user_id)


async def set_auto_scan_config(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    enabled: bool,
    start_date: date,
    frequency_minutes: int,
) -> AutoScanConfig:
    config = await session.get(AutoScanConfig, user_id)
    if config is None:
        config = AutoScanConfig(
            user_id=user_id, enabled=enabled, start_date=start_date, frequency_minutes=frequency_minutes
        )
        session.add(config)
    else:
        config.enabled = enabled
        config.start_date = start_date
        config.frequency_minutes = frequency_minutes
    await session.flush()
    return config


def _is_due(config: AutoScanConfig, now: datetime) -> bool:
    if config.last_run_at is None:
        return True
    last_run_at = config.last_run_at
    if last_run_at.tzinfo is None:  # SQLite in tests drops tzinfo on round-trip
        last_run_at = last_run_at.replace(tzinfo=timezone.utc)
    return now - last_run_at >= timedelta(minutes=config.frequency_minutes)


async def run_due_auto_scans(session: AsyncSession) -> int:
    """Runs a scan for every enabled config that's due. Returns how many ran.
    One user's failure (no Google connection, an expired token, ...) must
    never stop the rest — each is isolated in its own try/except."""
    now = datetime.now(timezone.utc)
    configs = list(await session.scalars(select(AutoScanConfig).where(AutoScanConfig.enabled.is_(True))))

    ran = 0
    for config in configs:
        if not _is_due(config, now):
            continue
        ran += 1
        try:
            run = await run_scan(
                session, user_id=config.user_id, start_date=config.start_date, end_date=None, force=False
            )
            config.last_status = run.status
        except (GoogleNotConnected, GoogleOAuthError):
            config.last_status = "not_connected"
        except Exception as exc:  # noqa: BLE001 - this user's failure, not the whole tick's
            config.last_status = "error"
            print(f"[auto-scan] user {config.user_id}: {type(exc).__name__}: {exc}", flush=True)
        config.last_run_at = now
        await session.flush()
    return ran


async def auto_scan_loop(poll_seconds: int = 60) -> None:
    """Runs forever (until cancelled) — call via asyncio.create_task from the
    app's lifespan, one task for the whole process, not per-request."""
    while True:
        try:
            async with SessionLocal() as session:
                ran = await run_due_auto_scans(session)
                await session.commit()
                if ran:
                    print(f"[auto-scan] ran {ran} due scan(s)", flush=True)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - the loop must survive a bad tick
            print(f"[auto-scan] tick failed: {type(exc).__name__}: {exc}", flush=True)
        await asyncio.sleep(poll_seconds)
