"""Chat endpoint — runs one agent turn and streams events as SSE."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.loop import run_agent_turn
from app.auth.deps import get_current_user
from app.db.models import User
from app.db.session import SessionLocal

router = APIRouter(prefix="/chat", tags=["chat"])


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
