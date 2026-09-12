import pytest

from app.integrations import sheets


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

    async def post(self, url, **kwargs):
        return self._responses.pop(0)

    async def put(self, url, **kwargs):
        return self._responses.pop(0)


def _patch_client(monkeypatch, responses):
    monkeypatch.setattr(sheets.httpx, "AsyncClient", lambda *a, **k: _FakeAsyncClient(responses))


def test_header_row_matches_last_col():
    assert len(sheets.HEADER_ROW) == 9
    assert sheets.HEADER_ROW == [
        "Date", "Job Title", "Company", "Salary", "Requirements", "Status", "Platform", "Next Action", "Last Updated",
    ]
    assert sheets.LAST_COL == "I"


async def test_create_tracker_spreadsheet(monkeypatch):
    _patch_client(monkeypatch, [_FakeResponse(200, {"spreadsheetId": "sheet123"}), _FakeResponse(200, {})])
    result = await sheets.create_tracker_spreadsheet("token")
    assert result == {"id": "sheet123", "url": "https://docs.google.com/spreadsheets/d/sheet123/edit"}


async def test_create_tracker_spreadsheet_create_failure(monkeypatch):
    _patch_client(monkeypatch, [_FakeResponse(403, text="nope")])
    with pytest.raises(sheets.SheetsError):
        await sheets.create_tracker_spreadsheet("token")


async def test_create_tracker_spreadsheet_header_failure(monkeypatch):
    _patch_client(monkeypatch, [_FakeResponse(200, {"spreadsheetId": "sheet123"}), _FakeResponse(500, text="boom")])
    with pytest.raises(sheets.SheetsError):
        await sheets.create_tracker_spreadsheet("token")


async def test_append_row_returns_row_number(monkeypatch):
    _patch_client(monkeypatch, [_FakeResponse(200, {"updates": {"updatedRange": "Applications!A5:F5"}})])
    row_number = await sheets.append_row("token", "sheet123", ["Acme", "BE", "applied", "", "", "manual"])
    assert row_number == 5


async def test_append_row_failure(monkeypatch):
    _patch_client(monkeypatch, [_FakeResponse(429, text="rate limited")])
    with pytest.raises(sheets.SheetsError):
        await sheets.append_row("token", "sheet123", ["x"])


async def test_update_row(monkeypatch):
    _patch_client(monkeypatch, [_FakeResponse(200, {})])
    await sheets.update_row("token", "sheet123", 5, ["Acme", "BE", "interview", "", "", "manual"])


async def test_update_row_failure(monkeypatch):
    _patch_client(monkeypatch, [_FakeResponse(500, text="boom")])
    with pytest.raises(sheets.SheetsError):
        await sheets.update_row("token", "sheet123", 5, ["x"])
