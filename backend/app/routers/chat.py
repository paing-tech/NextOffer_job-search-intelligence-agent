"""Chat endpoint — runs one agent turn and streams events as SSE."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.loop import run_agent_turn
from app.auth.deps import get_current_user
from app.db.models import User
from app.db.session import SessionLocal, get_session
from app.services.chat_history import get_chat_session_messages, list_chat_sessions

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/sessions")
async def list_sessions(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return {"sessions": await list_chat_sessions(session, user_id=user.id)}


@router.get("/sessions/{session_id}")
async def get_session_transcript(
    session_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        sid = uuid.UUID(session_id)
    except ValueError as exc:
        raise HTTPException(400, "Invalid id") from exc
    messages = await get_chat_session_messages(session, user_id=user.id, session_id=sid)
    if messages is None:
        raise HTTPException(404, "Not found")
    return {"id": session_id, "messages": messages}


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    chat_session_id: str | None = None


@router.post("")
async def chat(body: ChatRequest, user: User = Depends(get_current_user)) -> StreamingResponse:
    async def event_stream() -> AsyncIterator[bytes]:
        # Own session so the generator controls its own commit lifecycle.
        async with SessionLocal() as session:  # type: AsyncSession
            try:
                async for event in run_agent_turn(session, user, body.message, body.chat_session_id):
                    yield f"data: {json.dumps(event)}\n\n".encode()
                await session.commit()
            except Exception as exc:  # surface a clean error frame to the client
                await session.rollback()
                yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n".encode()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
