"""Read endpoints for the tracked applications list."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.models import Application, User
from app.db.session import get_session
from app.services.applications import search_applications, serialize_application

router = APIRouter(prefix="/applications", tags=["applications"])


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
    return serialize_application(app, include_events=True)
