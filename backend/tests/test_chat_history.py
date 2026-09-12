import uuid
from datetime import datetime, timezone

from app.db.models import ChatMessage, ChatSession, User
from app.services.chat_history import get_chat_session_messages, list_chat_sessions


async def _make_session(session, user_id, *, title=None):
    cs = ChatSession(user_id=user_id, title=title)
    session.add(cs)
    await session.flush()
    return cs


async def test_list_chat_sessions_empty(session, user):
    assert await list_chat_sessions(session, user_id=user.id) == []


async def test_list_chat_sessions_derives_title_from_first_user_message(session, user):
    cs = await _make_session(session, user.id)
    session.add(ChatMessage(session_id=cs.id, role="user", content="Analyze this job link please"))
    session.add(ChatMessage(session_id=cs.id, role="assistant", content="Sure, one sec."))
    await session.flush()

    sessions = await list_chat_sessions(session, user_id=user.id)
    assert len(sessions) == 1
    assert sessions[0]["id"] == str(cs.id)
    assert sessions[0]["title"] == "Analyze this job link please"


async def test_list_chat_sessions_keeps_explicit_title(session, user):
    cs = await _make_session(session, user.id, title="Custom title")
    session.add(ChatMessage(session_id=cs.id, role="user", content="hello"))
    await session.flush()

    sessions = await list_chat_sessions(session, user_id=user.id)
    assert sessions[0]["title"] == "Custom title"


async def test_list_chat_sessions_orders_newest_updated_first(session, user):
    cs1 = await _make_session(session, user.id)
    cs2 = await _make_session(session, user.id)
    cs1.updated_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    cs2.updated_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    await session.flush()

    sessions = await list_chat_sessions(session, user_id=user.id)
    assert [s["id"] for s in sessions] == [str(cs2.id), str(cs1.id)]


async def test_get_chat_session_messages_filters_out_tool_and_empty_assistant_rows(session, user):
    cs = await _make_session(session, user.id)
    session.add(ChatMessage(session_id=cs.id, role="user", content="track this job"))
    session.add(ChatMessage(session_id=cs.id, role="assistant", content="", tool_calls=[{"id": "1"}]))
    session.add(ChatMessage(session_id=cs.id, role="tool", content='{"status":"ok"}', tool_call_id="1"))
    session.add(ChatMessage(session_id=cs.id, role="assistant", content="Done, tracked it."))
    await session.flush()

    messages = await get_chat_session_messages(session, user_id=user.id, session_id=cs.id)
    assert messages == [
        {"role": "user", "content": "track this job"},
        {"role": "assistant", "content": "Done, tracked it."},
    ]


async def test_get_chat_session_messages_returns_none_for_missing_or_other_users_session(session, user):
    assert await get_chat_session_messages(session, user_id=user.id, session_id=uuid.uuid4()) is None

    other_user = User(id=uuid.uuid4(), email="other@example.com")
    session.add(other_user)
    await session.flush()
    cs = await _make_session(session, other_user.id)
    assert await get_chat_session_messages(session, user_id=user.id, session_id=cs.id) is None
