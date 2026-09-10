"""Best-effort retrieval of a job posting from a URL.

LinkedIn, JobStreet, Seek and friends aggressively gate their postings. We try a
plain HTTP fetch with readable-content extraction; when the result looks like a
login wall or is too thin to be a real posting, we return ``needs_paste=True`` so
the caller can ask the user to paste the description text instead.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)
_MIN_CHARS = 400
_WALL_MARKERS = (
    "sign in to continue",
    "sign in to see",
    "join linkedin",
    "please enable javascript",
    "you must be logged in",
    "create an account to continue",
    "captcha",
    "access denied",
)
_PLATFORMS = {
    "linkedin.": "linkedin",
    "jobstreet.": "jobstreet",
    "indeed.": "indeed",
    "seek.": "seek",
    "glassdoor.": "glassdoor",
    "lever.co": "lever",
    "greenhouse.io": "greenhouse",
}


@dataclass
class FetchResult:
    platform: str
    text: str
    needs_paste: bool
    reason: str | None = None
    final_url: str | None = None


def detect_platform(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    for needle, name in _PLATFORMS.items():
        if needle in host:
            return name
    return "generic"


def _extract_main_text(html: str) -> str:
    try:
        import trafilatura

        extracted = trafilatura.extract(html, include_comments=False, include_tables=False)
        if extracted:
            return extracted.strip()
    except Exception:  # pragma: no cover - trafilatura optional/parse issues
        pass

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "svg"]):
        tag.decompose()
    text = re.sub(r"\n{3,}", "\n\n", soup.get_text("\n"))
    return text.strip()


def _looks_walled(text: str) -> bool:
    low = text.lower()
    if len(text) < _MIN_CHARS:
        return True
    return any(marker in low for marker in _WALL_MARKERS) and len(text) < 2500


async def fetch_posting(url: str, *, timeout: float = 12.0) -> FetchResult:
    platform = detect_platform(url)
    headers = {"User-Agent": _UA, "Accept-Language": "en;q=0.9", "Accept": "text/html"}
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, headers=headers) as client:
            resp = await client.get(url)
    except httpx.HTTPError as exc:
        return FetchResult(platform, "", needs_paste=True, reason=f"Could not reach the page ({exc}).")

    if resp.status_code >= 400:
        return FetchResult(
            platform, "", needs_paste=True, reason=f"The site returned HTTP {resp.status_code}.", final_url=str(resp.url)
        )

    text = _extract_main_text(resp.text)
    if _looks_walled(text):
        return FetchResult(
            platform,
            text,
            needs_paste=True,
            reason="The posting appears to be behind a login wall or rendered client-side.",
            final_url=str(resp.url),
        )
    return FetchResult(platform, text[:24000], needs_paste=False, final_url=str(resp.url))
