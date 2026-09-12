"""Application-tracking domain logic shared by the REST routers and the agent tools."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    STATUS_LABELS,
    STATUS_RANK,
    STATUS_TO_EVENT_TYPE,
    Application,
    ApplicationEvent,
    ApplicationSource,
    ApplicationStatus,
    EventType,
    JobPosting,
)
from app.services.formatting import format_requirements
from app.services.sheets_sync import sync_application


async def fields_from_job_posting(session: AsyncSession, job_posting_id: uuid.UUID) -> dict:
    """salary/requirements/platform to seed onto an Application when tracking a posting."""
    posting = await session.get(JobPosting, job_posting_id)
    if posting is None:
        return {}
    return {
        "salary": posting.salary_text,
        "requirements": format_requirements(posting.skills, posting.experience_requirements),
        "platform": posting.source_platform,
    }


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
        "salary": app.salary,
        "requirements": app.requirements,
        "platform": app.platform,
        "job_posting_id": str(app.job_posting_id) if app.job_posting_id else None,
        "first_seen_at": app.first_seen_at.isoformat() if app.first_seen_at else None,
        "status_changed_at": app.status_changed_at.isoformat() if app.status_changed_at else None,
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
    salary: str | None = None,
    requirements: str | None = None,
    platform: str | None = None,
    status_confidence: float | None = None,
    event: tuple[EventType, str] | None = None,
    occurred_at: datetime | None = None,
) -> tuple[Application, bool]:
    """Create or update an application by (user, company, title). Returns (app, created).

    `occurred_at` is when the status-driving event actually happened in the real
    world (e.g. the Gmail message's Date header) — as opposed to "now", which is
    merely when we happened to process it. When given, it backdates
    `status_changed_at` and the logged `ApplicationEvent.occurred_at` so a scan
    run days after an email arrived (or a force-rescan of old mail) still shows
    the true date. `last_update_at` always reflects real processing time.
    """
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
        status=status or ApplicationStatus.saved,
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
    if salary is not None:
        app.salary = salary
    if requirements is not None:
        app.requirements = requirements
    if platform is not None:
        app.platform = platform
    if status_confidence is not None:
        app.status_confidence = status_confidence

    now = datetime.now(timezone.utc)
    change_at = occurred_at or now
    previous_status = app.status
    # Only move status forward (or to a terminal state); never regress interview -> applied.
    if status is not None and STATUS_RANK.get(status, 0) >= STATUS_RANK.get(app.status, 0):
        app.status = status
    status_changed = created or app.status != previous_status
    if status_changed:
        app.status_changed_at = change_at
    app.last_update_at = now

    if event is not None:
        await session.flush()
        etype, summary = event
        ev = ApplicationEvent(application_id=app.id, event_type=etype, summary=summary)
        if occurred_at is not None:
            ev.occurred_at = occurred_at
        session.add(ev)
    elif status_changed and not created:
        # No explicit event supplied but the status genuinely moved — auto-log it so
        # the modal's history stays complete even for status changes made outside
        # the scan pipeline (e.g. tracking a link, or the chat agent).
        await session.flush()
        etype = STATUS_TO_EVENT_TYPE.get(app.status, EventType.status_update)
        summary = f"Status changed to {STATUS_LABELS.get(app.status, app.status.value)}."
        ev = ApplicationEvent(application_id=app.id, event_type=etype, summary=summary)
        if occurred_at is not None:
            ev.occurred_at = occurred_at
        session.add(ev)

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
