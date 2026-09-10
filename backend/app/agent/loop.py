"""The agent loop: build context, call the model, dispatch tools, persist history."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.agent.prompts import SYSTEM_PROMPT, build_context_block
from app.agent.tools import TOOL_SPECS, ToolContext, run_tool
from app.db.models import ChatMessage, ChatSession, User
from app.llm.client import complete

_settings = get_settings()


async def _load_session(session: AsyncSession, user_id: uuid.UUID, chat_session_id: str | None) -> ChatSession:
    if chat_session_id:
        try:
            cs = await session.get(ChatSession, uuid.UUID(chat_session_id))
        except ValueError:
            cs = None
        if cs and cs.user_id == user_id:
            return cs
    cs = ChatSession(user_id=user_id)
    session.add(cs)
    await session.flush()
    return cs


def _history_to_messages(messages: list[ChatMessage]) -> list[dict]:
    out: list[dict] = []
    for m in messages:
        if m.role == "assistant" and m.tool_calls:
            out.append({"role": "assistant", "content": m.content or None, "tool_calls": m.tool_calls})
        elif m.role == "tool":
            out.append({"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content})
        else:
            out.append({"role": m.role, "content": m.content})
    return out


async def run_agent_turn(
    session: AsyncSession,
    user: User,
    message: str,
    chat_session_id: str | None = None,
) -> AsyncIterator[dict]:
    cs = await _load_session(session, user.id, chat_session_id)
    yield {"type": "session", "chat_session_id": str(cs.id)}

    prior = list(
        await session.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == cs.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(_settings.chat_history_window)
        )
    )
    prior.reverse()

    session.add(ChatMessage(session_id=cs.id, role="user", content=message))
    await session.flush()

    context_block = await build_context_block(session, user.id)
    convo: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": context_block},
        *_history_to_messages(prior),
        {"role": "user", "content": message},
    ]

    ctx = ToolContext(session=session, user_id=user.id)
    last_structured: dict | None = None
    final_text = ""

    for _ in range(_settings.agent_max_tool_iterations):
        result = await complete(convo, tools=TOOL_SPECS, tool_choice="auto", max_tokens=1500)

        if not result.has_tool_calls:
            final_text = result.text or ""
            break

        assistant_tool_calls = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
            }
            for tc in result.tool_calls
        ]
        convo.append({"role": "assistant", "content": result.text or None, "tool_calls": assistant_tool_calls})
        session.add(
            ChatMessage(
                session_id=cs.id, role="assistant", content=result.text or "", tool_calls=assistant_tool_calls
            )
        )

        for tc in result.tool_calls:
            yield {"type": "tool", "name": tc.name}
            tool_result = await run_tool(tc.name, tc.arguments, ctx)
            if tc.name == "analyze_job_link" and tool_result.get("status") in {"ok", "needs_paste"}:
                last_structured = tool_result
            payload = json.dumps(tool_result)
            convo.append({"role": "tool", "tool_call_id": tc.id, "content": payload})
            session.add(
                ChatMessage(session_id=cs.id, role="tool", content=payload, tool_call_id=tc.id)
            )
        await session.flush()
    else:
        final_text = final_text or "I've stopped after several steps — could you rephrase or narrow the request?"

    session.add(ChatMessage(session_id=cs.id, role="assistant", content=final_text))
    await session.flush()

    yield {"type": "final", "text": final_text, "data": last_structured, "chat_session_id": str(cs.id)}
