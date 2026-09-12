"""Read-side chat history: list a user's past chat sessions and fetch one
session's displayable transcript. Writing to ChatSession/ChatMessage happens
in agent/loop.py as part of running a turn — this module only reads.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChatMessage, ChatSession


def _derive_title(first_user_message: str | None) -> str:
    """Sessions never get an explicit title today, so fall back to a
    truncated version of the first thing the user said."""
    if not first_user_message:
        return "New chat"
    text = " ".join(first_user_message.split())
    return text[:60] + ("…" if len(text) > 60 else "")


async def list_chat_sessions(session: AsyncSession, *, user_id: uuid.UUID, limit: int = 50) -> list[dict]:
    sessions = list(
        await session.scalars(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
        )
    )
    out: list[dict] = []
    for cs in sessions:
        first_user_message = (
            await session.scalars(
                select(ChatMessage.content)
                .where(ChatMessage.session_id == cs.id, ChatMessage.role == "user")
                .order_by(ChatMessage.created_at.asc())
                .limit(1)
            )
        ).first()
        out.append(
            {
                "id": str(cs.id),
                "title": cs.title or _derive_title(first_user_message),
                "updated_at": cs.updated_at.isoformat() if cs.updated_at else None,
                "created_at": cs.created_at.isoformat() if cs.created_at else None,
            }
        )
    return out


async def get_chat_session_messages(
    session: AsyncSession, *, user_id: uuid.UUID, session_id: uuid.UUID
) -> list[dict] | None:
    """Returns None if the session doesn't exist or isn't this user's."""
    cs = await session.get(ChatSession, session_id)
    if cs is None or cs.user_id != user_id:
        return None

    rows = list(
        await session.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id, ChatMessage.role.in_(("user", "assistant")))
            .order_by(ChatMessage.created_at.asc())
        )
    )
    out: list[dict] = []
    for m in rows:
        if m.role == "assistant" and not m.content:
            continue  # a tool-call-only turn — nothing user-visible to replay
        out.append({"role": m.role, "content": m.content})
    return out
