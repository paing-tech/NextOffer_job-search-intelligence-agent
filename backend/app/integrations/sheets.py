"""Google Sheets: create the tracker spreadsheet, append/update application rows.

Raw REST (httpx) against the Sheets API v4, same reasoning as google_oauth.py —
this app is async end to end and these are a handful of well-documented calls.
"""

from __future__ import annotations

import httpx

SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"
SHEET_NAME = "Applications"
HEADER_ROW = [
    "Date", "Job Title", "Company", "Salary", "Requirements", "Status", "Platform", "Next Action", "Last Updated",
]
LAST_COL = "I"  # keep in sync with len(HEADER_ROW)


class SheetsError(RuntimeError):
    pass


def _headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}


async def create_tracker_spreadsheet(access_token: str, *, title: str = "NextOffer Job Tracker") -> dict:
    """Create a new spreadsheet with a header row. Returns {id, url}."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            SHEETS_API,
            headers=_headers(access_token),
            json={
                "properties": {"title": title},
                "sheets": [{"properties": {"title": SHEET_NAME}}],
            },
        )
        if resp.status_code != 200:
            raise SheetsError(f"Could not create spreadsheet: {resp.status_code} {resp.text}")
        spreadsheet_id = resp.json()["spreadsheetId"]

        header = await client.put(
            f"{SHEETS_API}/{spreadsheet_id}/values/{SHEET_NAME}!A1:{LAST_COL}1",
            headers=_headers(access_token),
            params={"valueInputOption": "USER_ENTERED"},
            json={"values": [HEADER_ROW]},
        )
        if header.status_code != 200:
            raise SheetsError(f"Spreadsheet created but header row failed: {header.status_code} {header.text}")

    return {"id": spreadsheet_id, "url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"}


async def append_row(access_token: str, spreadsheet_id: str, row: list[str]) -> int:
    """Append one row; returns its 1-indexed row number for later updates."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{SHEETS_API}/{spreadsheet_id}/values/{SHEET_NAME}!A:{LAST_COL}:append",
            headers=_headers(access_token),
            params={"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"},
            json={"values": [row]},
        )
    if resp.status_code != 200:
        raise SheetsError(f"Could not append row: {resp.status_code} {resp.text}")
    # updatedRange looks like "Applications!A5:F5" — pull the row number back out.
    updated_range: str = resp.json()["updates"]["updatedRange"]
    cell_ref = updated_range.split("!")[1].split(":")[0]
    return int("".join(ch for ch in cell_ref if ch.isdigit()))


async def update_row(access_token: str, spreadsheet_id: str, row_number: int, row: list[str]) -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.put(
            f"{SHEETS_API}/{spreadsheet_id}/values/{SHEET_NAME}!A{row_number}:{LAST_COL}{row_number}",
            headers=_headers(access_token),
            params={"valueInputOption": "USER_ENTERED"},
            json={"values": [row]},
        )
    if resp.status_code != 200:
        raise SheetsError(f"Could not update row {row_number}: {resp.status_code} {resp.text}")
