"""Application-tracking domain logic shared by the REST routers and the agent tools."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    STATUS_RANK,
    Application,
    ApplicationEvent,
    ApplicationSource,
    ApplicationStatus,
    EventType,
)
from app.services.sheets_sync import sync_application


def dedupe_key(company: str, job_title: str) -> str:
    def norm(value: str) -> str:
        value = re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()
        return re.sub(r"\s+", " ", value)

    return f"{norm(company)}::{norm(job_title)}"


def serialize_application(app: Application, *, include_events: bool = False) -> dict:
    data = {
        "id": str(app.id),
        "company": app.company,
        "job_title": app.job_title,
        "status": app.status.value,
        "status_confidence": app.status_confidence,
        "source": app.source.value,
        "next_action": app.next_action,
        "next_action_due": app.next_action_due.isoformat() if app.next_action_due else None,
        "job_posting_id": str(app.job_posting_id) if app.job_posting_id else None,
        "first_seen_at": app.first_seen_at.isoformat() if app.first_seen_at else None,
        "last_update_at": app.last_update_at.isoformat() if app.last_update_at else None,
    }
    if include_events:
        data["events"] = [
            {
                "id": str(e.id),
                "event_type": e.event_type.value,
                "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
                "summary": e.summary,
            }
            for e in app.events
        ]
    return data


async def upsert_application(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    company: str,
    job_title: str,
    status: ApplicationStatus | None = None,
    source: ApplicationSource = ApplicationSource.manual,
    next_action: str | None = None,
    next_action_due: datetime | None = None,
    job_posting_id: uuid.UUID | None = None,
    status_confidence: float | None = None,
    event: tuple[EventType, str] | None = None,
) -> tuple[Application, bool]:
    """Create or update an application by (user, company, title). Returns (app, created)."""
    key = dedupe_key(company, job_title)
    existing = (
        await session.scalars(
            select(Application).where(Application.user_id == user_id, Application.dedupe_key == key)
        )
    ).first()

    created = existing is None
    app = existing or Application(
        user_id=user_id,
        company=company.strip(),
        job_title=job_title.strip(),
        dedupe_key=key,
        status=status or ApplicationStatus.discovered,
        source=source,
    )
    if created:
        session.add(app)

    if next_action is not None:
        app.next_action = next_action
    if next_action_due is not None:
        app.next_action_due = next_action_due
    if job_posting_id is not None:
        app.job_posting_id = job_posting_id
    if status_confidence is not None:
        app.status_confidence = status_confidence
    # Only move status forward (or to a terminal state); never regress interview -> applied.
    if status is not None and STATUS_RANK.get(status, 0) >= STATUS_RANK.get(app.status, 0):
        app.status = status
    app.last_update_at = datetime.now(timezone.utc)

    if event is not None:
        await session.flush()
        etype, summary = event
        session.add(ApplicationEvent(application_id=app.id, event_type=etype, summary=summary))

    await session.flush()
    await sync_application(session, user_id=user_id, application=app)
    return app, created


async def search_applications(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    query: str | None = None,
    status: str | None = None,
    limit: int = 25,
) -> list[Application]:
    stmt = select(Application).where(Application.user_id == user_id).order_by(Application.last_update_at.desc())
    if status:
        stmt = stmt.where(Application.status == ApplicationStatus(status))
    if query:
        like = f"%{query.lower()}%"
        stmt = stmt.where(
            (Application.company.ilike(like)) | (Application.job_title.ilike(like))
        )
    return list(await session.scalars(stmt.limit(limit)))
