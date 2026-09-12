"""Read endpoints for the tracked applications list."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.models import Application, ApplicationSource, ApplicationStatus, JobPosting, User
from app.db.session import get_session
from app.services.applications import (
    fields_from_job_posting,
    search_applications,
    serialize_application,
    upsert_application,
)
from app.services.jobs import serialize_posting

router = APIRouter(prefix="/applications", tags=["applications"])


class UpsertApplicationRequest(BaseModel):
    company: str = Field(min_length=1, max_length=255)
    job_title: str = Field(min_length=1, max_length=255)
    status: ApplicationStatus | None = None
    next_action: str | None = None
    job_posting_id: str | None = None


@router.post("", status_code=201)
async def create_or_update_application(
    body: UpsertApplicationRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    posting_id = None
    if body.job_posting_id:
        try:
            posting_id = uuid.UUID(body.job_posting_id)
        except ValueError as exc:
            raise HTTPException(400, "Invalid job_posting_id") from exc

    derived = await fields_from_job_posting(session, posting_id) if posting_id else {}

    app, created = await upsert_application(
        session,
        user_id=user.id,
        company=body.company,
        job_title=body.job_title,
        status=body.status,
        source=ApplicationSource.link if posting_id else ApplicationSource.manual,
        next_action=body.next_action,
        job_posting_id=posting_id,
        **derived,
    )
    return {"created": created, "application": serialize_application(app)}


@router.get("")
async def list_applications(
    query: str | None = None,
    status: str | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    apps = await search_applications(session, user_id=user.id, query=query, status=status, limit=100)
    return {"applications": [serialize_application(a) for a in apps]}


@router.get("/{application_id}")
async def get_application(
    application_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        app_id = uuid.UUID(application_id)
    except ValueError as exc:
        raise HTTPException(400, "Invalid id") from exc
    app = await session.get(Application, app_id)
    if app is None or app.user_id != user.id:
        raise HTTPException(404, "Not found")
    await session.refresh(app, ["events"])
    data = serialize_application(app, include_events=True)

    if app.job_posting_id:
        posting = await session.get(JobPosting, app.job_posting_id)
        if posting is not None:
            data["job_posting"] = serialize_posting(posting)

    return data
