"""Gmail: build a date-bounded search query, list matching messages, fetch and
decode their plain-text body for classification."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import date, timedelta

import httpx

GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
MAX_RESULTS_DEFAULT = 150

# Gmail search does the cheap first-pass filtering; the LLM still confirms
# each candidate is actually job-related and extracts details — this just
# keeps the candidate set small.
JOB_KEYWORDS = (
    'interview OR applied OR application OR assessment OR offer OR rejected OR '
    '"thank you for applying" OR position OR "your application" OR recruiter OR '
    'hiring OR onboarding OR candidacy'
)


class GmailError(RuntimeError):
    pass


@dataclass
class GmailMessage:
    id: str
    thread_id: str
    subject: str
    sender: str
    date: str
    body_text: str


def build_query(start_date: date, end_date: date | None) -> str:
    """`end_date=None` means "up to now" — no upper bound at all."""
    parts = [f"after:{start_date.strftime('%Y/%m/%d')}"]
    if end_date:
        # Gmail's before: excludes that day, so add one to make end_date inclusive.
        parts.append(f"before:{(end_date + timedelta(days=1)).strftime('%Y/%m/%d')}")
    parts.append(f"({JOB_KEYWORDS})")
    return " ".join(parts)


def _header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _decode_part(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def _walk_parts(payload: dict) -> tuple[str | None, str | None]:
    """Returns (plain_text, html_text) found anywhere in the MIME tree."""
    plain = html = None
    body_data = (payload.get("body") or {}).get("data")
    if body_data:
        text = _decode_part(body_data)
        if payload.get("mimeType") == "text/plain":
            plain = text
        elif payload.get("mimeType") == "text/html":
            html = text
    for part in payload.get("parts") or []:
        p, h = _walk_parts(part)
        plain = plain or p
        html = html or h
    return plain, html


def extract_body_text(payload: dict) -> str:
    plain, html = _walk_parts(payload)
    if plain and plain.strip():
        return plain.strip()
    if html:
        from bs4 import BeautifulSoup

        return BeautifulSoup(html, "html.parser").get_text("\n").strip()
    return ""


async def list_message_ids(access_token: str, query: str, *, max_results: int = MAX_RESULTS_DEFAULT) -> list[str]:
    ids: list[str] = []
    page_token: str | None = None
    async with httpx.AsyncClient(timeout=15, headers={"Authorization": f"Bearer {access_token}"}) as client:
        while len(ids) < max_results:
            params: dict = {"q": query, "maxResults": min(100, max_results - len(ids))}
            if page_token:
                params["pageToken"] = page_token
            resp = await client.get(f"{GMAIL_API}/messages", params=params)
            if resp.status_code != 200:
                raise GmailError(f"Could not list messages: {resp.status_code} {resp.text}")
            data = resp.json()
            ids.extend(m["id"] for m in data.get("messages", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                break
    return ids[:max_results]


async def get_message(access_token: str, message_id: str) -> GmailMessage:
    async with httpx.AsyncClient(timeout=15, headers={"Authorization": f"Bearer {access_token}"}) as client:
        resp = await client.get(f"{GMAIL_API}/messages/{message_id}", params={"format": "full"})
    if resp.status_code != 200:
        raise GmailError(f"Could not fetch message {message_id}: {resp.status_code} {resp.text}")
    data = resp.json()
    payload = data.get("payload", {})
    headers = payload.get("headers", [])
    return GmailMessage(
        id=data["id"],
        thread_id=data.get("threadId", ""),
        subject=_header(headers, "Subject"),
        sender=_header(headers, "From"),
        date=_header(headers, "Date"),
        body_text=extract_body_text(payload)[:12000],
    )
