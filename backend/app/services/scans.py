"""Gmail scan pipeline: list candidate messages -> classify each -> upsert
applications/events -> mirror to the tracker sheet (via upsert_application).

Fetching + classifying (network/LLM, no DB) runs with bounded concurrency;
all database writes happen afterwards, sequentially, on the one session
passed in — AsyncSession is not safe to use concurrently from multiple tasks.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApplicationSource, ApplicationStatus, EventType, ProcessedEmail, ScanRun
from app.integrations.gmail import GmailError, GmailMessage, build_query, get_message, list_message_ids
from app.integrations.google_oauth import get_valid_access_token
from app.llm.extraction import classify_email
from app.llm.schemas import EmailClassification
from app.services.applications import upsert_application

_CONCURRENCY = 5

EVENT_TYPE_TO_STATUS = {
    EventType.applied: ApplicationStatus.applied,
    EventType.assessment: ApplicationStatus.assessment,
    EventType.interview: ApplicationStatus.interview,
    EventType.offer: ApplicationStatus.offer,
    EventType.rejection: ApplicationStatus.rejected,
}


def _parse_due_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def serialize_scan_run(run: ScanRun) -> dict:
    return {
        "id": str(run.id),
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "messages_scanned": run.messages_scanned,
        "events_created": run.events_created,
        "applications_updated": run.applications_updated,
        "error": run.error,
    }


async def _fetch_and_classify(
    access_token: str, message_id: str
) -> tuple[str, GmailMessage | None, EmailClassification | None, Exception | None]:
    try:
        msg = await get_message(access_token, message_id)
        if not msg.body_text.strip():
            return message_id, msg, None, None
        classification, _usage = await classify_email(
            subject=msg.subject, sender=msg.sender, date=msg.date, body_text=msg.body_text
        )
        return message_id, msg, classification, None
    except Exception as exc:  # noqa: BLE001 - one bad message must not sink the whole scan
        return message_id, None, None, exc


async def run_scan(
    session: AsyncSession, *, user_id: uuid.UUID, start_date: date, end_date: date | None
) -> ScanRun:
    """Raises GoogleNotConnected if the user hasn't connected Google — that's a
    setup problem for the caller to report, not a per-message scan failure."""
    access_token = await get_valid_access_token(session, user_id)

    run = ScanRun(user_id=user_id, status="running")
    session.add(run)
    await session.flush()

    try:
        query = build_query(start_date, end_date)
        candidate_ids = await list_message_ids(access_token, query)

        already_seen: set[str] = set()
        if candidate_ids:
            already_seen = set(
                await session.scalars(
                    select(ProcessedEmail.gmail_message_id).where(
                        ProcessedEmail.user_id == user_id,
                        ProcessedEmail.gmail_message_id.in_(candidate_ids),
                    )
                )
            )
        new_ids = [mid for mid in candidate_ids if mid not in already_seen]

        semaphore = asyncio.Semaphore(_CONCURRENCY)

        async def bounded(mid: str):
            async with semaphore:
                return await _fetch_and_classify(access_token, mid)

        results = await asyncio.gather(*(bounded(mid) for mid in new_ids))

        for message_id, _msg, classification, error in results:
            run.messages_scanned += 1
            if error is not None or classification is None:
                session.add(ProcessedEmail(user_id=user_id, gmail_message_id=message_id, classification="error"))
                continue

            application_id = None
            if classification.job_related and classification.company and classification.job_title:
                event_type = (
                    EventType(classification.event_type)
                    if classification.event_type in EventType.__members__
                    else EventType.other
                )
                app, created = await upsert_application(
                    session,
                    user_id=user_id,
                    company=classification.company,
                    job_title=classification.job_title,
                    status=EVENT_TYPE_TO_STATUS.get(event_type),
                    source=ApplicationSource.email,
                    next_action=classification.next_action,
                    next_action_due=_parse_due_date(classification.next_action_due),
                    event=(event_type, classification.summary),
                )
                application_id = app.id
                run.events_created += 1
                if not created:
                    run.applications_updated += 1

            session.add(
                ProcessedEmail(
                    user_id=user_id,
                    gmail_message_id=message_id,
                    classification="job_related" if classification.job_related else "not_related",
                    application_id=application_id,
                )
            )
        run.status = "completed"
    except GmailError as exc:
        run.status = "failed"
        run.error = str(exc)[:2000]
    except Exception as exc:  # noqa: BLE001 - record it on the run rather than a bare 500
        run.status = "failed"
        run.error = str(exc)[:2000]

    run.finished_at = datetime.now(timezone.utc)
    await session.flush()
    return run
