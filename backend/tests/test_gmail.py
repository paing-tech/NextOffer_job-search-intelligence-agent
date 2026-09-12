import base64
from datetime import date

from app.integrations import gmail


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode()


def test_build_query_open_ended():
    q = gmail.build_query(date(2026, 1, 1), None)
    assert q.startswith("after:2026/01/01")
    assert "before:" not in q
    assert "interview" in q


def test_build_query_bounded_is_inclusive_of_end_date():
    q = gmail.build_query(date(2026, 1, 1), date(2026, 1, 31))
    assert "after:2026/01/01" in q
    assert "before:2026/02/01" in q  # one day past end_date, since before: excludes that day


def test_extract_body_text_prefers_plain():
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/html", "body": {"data": _b64("<p>hi</p>")}},
            {"mimeType": "text/plain", "body": {"data": _b64("hi there")}},
        ],
    }
    assert gmail.extract_body_text(payload) == "hi there"


def test_extract_body_text_falls_back_to_html():
    payload = {"mimeType": "text/html", "body": {"data": _b64("<p>Only <b>html</b> here</p>")}}
    text = gmail.extract_body_text(payload)
    assert "Only" in text and "html" in text and "<b>" not in text


def test_extract_body_text_preserves_links_in_html_only_emails():
    # HTML-only emails (common for job-platform confirmations) would otherwise
    # silently lose their job link, which the classifier needs to find.
    html = '<p>Your application for <a href="https://sg.jobstreet.com/job/123">Backend Engineer</a> was submitted.</p>'
    text = gmail.extract_body_text({"mimeType": "text/html", "body": {"data": _b64(html)}})
    assert "https://sg.jobstreet.com/job/123" in text
    assert "Backend Engineer" in text


def test_extract_body_text_nested_parts():
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "parts": [{"mimeType": "text/plain", "body": {"data": _b64("nested body")}}],
            }
        ],
    }
    assert gmail.extract_body_text(payload) == "nested body"


def test_extract_body_text_empty_when_no_body():
    assert gmail.extract_body_text({"mimeType": "multipart/mixed", "parts": []}) == ""


class _FakeResponse:
    def __init__(self, status_code, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self):
        return self._json


class _FakeAsyncClient:
    def __init__(self, responses):
        self._responses = list(responses)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, **kwargs):
        return self._responses.pop(0)


def _patch_client(monkeypatch, responses):
    monkeypatch.setattr(gmail.httpx, "AsyncClient", lambda *a, **k: _FakeAsyncClient(responses))


async def test_list_message_ids_single_page(monkeypatch):
    _patch_client(monkeypatch, [_FakeResponse(200, {"messages": [{"id": "a"}, {"id": "b"}]})])
    ids = await gmail.list_message_ids("token", "q")
    assert ids == ["a", "b"]


async def test_list_message_ids_paginates_until_cap(monkeypatch):
    _patch_client(
        monkeypatch,
        [
            _FakeResponse(200, {"messages": [{"id": "a"}], "nextPageToken": "p2"}),
            _FakeResponse(200, {"messages": [{"id": "b"}]}),
        ],
    )
    ids = await gmail.list_message_ids("token", "q", max_results=10)
    assert ids == ["a", "b"]


async def test_list_message_ids_error(monkeypatch):
    import pytest

    _patch_client(monkeypatch, [_FakeResponse(403, text="nope")])
    with pytest.raises(gmail.GmailError):
        await gmail.list_message_ids("token", "q")


async def test_get_message_parses_headers_and_body(monkeypatch):
    _patch_client(
        monkeypatch,
        [
            _FakeResponse(
                200,
                {
                    "id": "m1",
                    "threadId": "t1",
                    "payload": {
                        "mimeType": "text/plain",
                        "headers": [
                            {"name": "Subject", "value": "Your application"},
                            {"name": "From", "value": "hr@acme.com"},
                            {"name": "Date", "value": "Mon, 1 Jan 2026 00:00:00 +0000"},
                        ],
                        "body": {"data": _b64("Thanks for applying.")},
                    },
                },
            )
        ],
    )
    msg = await gmail.get_message("token", "m1")
    assert msg.subject == "Your application"
    assert msg.sender == "hr@acme.com"
    assert msg.body_text == "Thanks for applying."
