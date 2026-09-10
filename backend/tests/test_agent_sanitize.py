from app.agent.loop import _sanitize


def _roles(msgs):
    return [m["role"] for m in msgs]


def test_drops_orphan_tool_message():
    msgs = [
        {"role": "system", "content": "s"},
        {"role": "assistant", "content": "done"},
        {"role": "tool", "tool_call_id": "x", "content": "r"},
        {"role": "user", "content": "hi"},
    ]
    assert _roles(_sanitize(msgs)) == ["system", "assistant", "user"]


def test_keeps_valid_tool_call_pair():
    msgs = [
        {"role": "assistant", "content": None, "tool_calls": [{"id": "a", "type": "function", "function": {"name": "f", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "a", "content": "r"},
    ]
    assert _roles(_sanitize(msgs)) == ["assistant", "tool"]


def test_demotes_unanswered_tool_call():
    msgs = [
        {"role": "assistant", "content": None, "tool_calls": [{"id": "a", "type": "function", "function": {"name": "f", "arguments": "{}"}}]},
        {"role": "user", "content": "next"},
    ]
    out = _sanitize(msgs)
    assert _roles(out) == ["assistant", "user"]
    assert "tool_calls" not in out[0]
    assert out[0]["content"] == ""


def test_tool_call_missing_id_is_demoted():
    msgs = [
        {"role": "assistant", "content": "x", "tool_calls": [{"type": "function", "function": {"name": "f", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": None, "content": "r"},
    ]
    out = _sanitize(msgs)
    assert _roles(out) == ["assistant"]
    assert "tool_calls" not in out[0]
