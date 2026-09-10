"""Best-effort retrieval of a job posting from a URL.

Layered strategy (first hit wins):

1. Platform-specific endpoint that doesn't require login
   - LinkedIn: the guest job-posting fragment API
2. `JobPosting` JSON-LD embedded in the page — present even on many login-gated
   sites because Google Jobs indexes it, and it needs no JavaScript
3. Site data blobs (`__NEXT_DATA__`) for SEEK / JobStreet
4. Readable main-content extraction
5. Give up -> ``needs_paste=True`` so the caller asks for the description text
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)
_MIN_TEXT = 200
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
    "ashbyhq.com": "ashby",
    "workday": "workday",
}
_LINKEDIN_JOB_ID = re.compile(r"(?:jobs/view/|currentJobId=|jobPosting/)(\d{6,})")
_SEEK_JOB_ID = re.compile(r"/job/(\d{5,})")

# host -> (seek-request-brand, seek-request-country) for the SEEK/JobStreet GraphQL API
_SEEK_HOSTS = {
    "sg.jobstreet.com": ("jobstreet", "SG"),
    "www.jobstreet.com.sg": ("jobstreet", "SG"),
    "my.jobstreet.com": ("jobstreet", "MY"),
    "www.jobstreet.com.my": ("jobstreet", "MY"),
    "id.jobstreet.com": ("jobstreet", "ID"),
    "www.jobstreet.co.id": ("jobstreet", "ID"),
    "th.jobstreet.com": ("jobstreet", "TH"),
    "ph.jobstreet.com": ("jobstreet", "PH"),
    "www.jobstreet.com.ph": ("jobstreet", "PH"),
    "www.seek.com.au": ("seek", "AU"),
    "seek.com.au": ("seek", "AU"),
    "www.seek.co.nz": ("seek", "NZ"),
}
_SEEK_QUERY = (
    "query jobDetails($jobId: ID!) { jobDetails(id: $jobId) { job { "
    "title advertiser { name } content(platform: WEB) salary { label } "
    "location { label } workTypes { label } } } }"
)


@dataclass
class FetchResult:
    platform: str
    text: str
    needs_paste: bool
    reason: str | None = None
    final_url: str | None = None
    source: str | None = None  # which strategy produced the text


def detect_platform(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    for needle, name in _PLATFORMS.items():
        if needle in host:
            return name
    return "generic"


# --------------------------------------------------------------------------- #
# JSON-LD (schema.org JobPosting)
# --------------------------------------------------------------------------- #

def _iter_jsonld(data):
    if isinstance(data, list):
        for item in data:
            yield from _iter_jsonld(item)
    elif isinstance(data, dict):
        yield data
        if "@graph" in data:
            yield from _iter_jsonld(data["@graph"])


def _is_jobposting(node: dict) -> bool:
    t = node.get("@type")
    return t == "JobPosting" or (isinstance(t, (list, tuple)) and "JobPosting" in t)


def _jsonld_jobposting(html: str) -> dict | None:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all("script", type="application/ld+json"):
        raw = (tag.string or tag.get_text() or "").strip()
        if "JobPosting" not in raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for node in _iter_jsonld(data):
            if isinstance(node, dict) and _is_jobposting(node):
                return node
    return None


def _flatten(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return ", ".join(p for p in (_flatten(v) for v in value) if p)
    if isinstance(value, dict):
        for key in ("name", "value", "credentialCategory", "text", "@value", "description"):
            if value.get(key):
                return _flatten(value[key])
        if "monthsOfExperience" in value:
            try:
                months = int(value["monthsOfExperience"])
                return f"{months // 12}+ years experience" if months >= 12 else f"{months} months experience"
            except (TypeError, ValueError):
                return str(value["monthsOfExperience"])
        if "address" in value:  # schema.org Place wraps a PostalAddress
            return _flatten(value["address"])
        parts = [value.get("addressLocality"), value.get("addressRegion"), value.get("addressCountry")]
        return ", ".join(_flatten(p) for p in parts if p)
    return ""


def _salary_text(base) -> str:
    if not isinstance(base, dict):
        return _flatten(base)
    currency = base.get("currency") or ""
    val = base.get("value", base)
    if isinstance(val, dict):
        lo, hi = val.get("minValue"), val.get("maxValue")
        unit = val.get("unitText") or ""
        if lo and hi:
            return f"{currency} {lo}–{hi} {unit}".strip()
        if val.get("value"):
            return f"{currency} {val['value']} {unit}".strip()
    return ""


def _jobposting_to_text(node: dict) -> str:
    from bs4 import BeautifulSoup

    lines: list[str] = []

    def add(label: str, value) -> None:
        text = _flatten(value)
        if text:
            lines.append(f"{label}: {text}")

    add("Title", node.get("title"))
    add("Company", node.get("hiringOrganization"))
    add("Location", node.get("jobLocation"))
    if node.get("jobLocationType"):
        lines.append("Remote: yes")
    add("Employment type", node.get("employmentType"))
    add("Industry", node.get("industry"))
    add("Date posted", node.get("datePosted"))
    salary = _salary_text(node.get("baseSalary"))
    if salary:
        lines.append(f"Salary: {salary}")
    add("Experience", node.get("experienceRequirements"))
    add("Education", node.get("educationRequirements"))
    add("Skills", node.get("skills"))
    add("Qualifications", node.get("qualifications"))
    add("Responsibilities", node.get("responsibilities"))

    description = node.get("description") or ""
    if description:
        body = BeautifulSoup(description, "html.parser").get_text("\n")
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        if body:
            lines.append("\nDescription:\n" + body)
    return "\n".join(lines).strip()


# --------------------------------------------------------------------------- #
# LinkedIn guest fragment
# --------------------------------------------------------------------------- #

def _linkedin_job_id(url: str) -> str | None:
    m = _LINKEDIN_JOB_ID.search(url)
    return m.group(1) if m else None


async def _fetch_linkedin_guest(job_id: str, client: httpx.AsyncClient) -> str | None:
    url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    try:
        resp = await client.get(url)
    except httpx.HTTPError:
        return None
    if resp.status_code != 200 or len(resp.text) < 300:
        return None

    from bs4 import BeautifulSoup

    node = _jsonld_jobposting(resp.text)
    if node:
        return _jobposting_to_text(node)

    soup = BeautifulSoup(resp.text, "html.parser")
    bits: list[str] = []
    for sel in (".top-card-layout__title", ".topcard__title", "h2"):
        el = soup.select_one(sel)
        if el:
            bits.append(f"Title: {el.get_text(' ', strip=True)}")
            break
    for sel in (".topcard__org-name-link", ".topcard__flavor a"):
        el = soup.select_one(sel)
        if el:
            bits.append(f"Company: {el.get_text(' ', strip=True)}")
            break
    el = soup.select_one(".topcard__flavor--bullet")
    if el:
        bits.append(f"Location: {el.get_text(' ', strip=True)}")
    for item in soup.select(".description__job-criteria-item"):
        head = item.select_one(".description__job-criteria-subheader")
        val = item.select_one(".description__job-criteria-text")
        if head and val:
            bits.append(f"{head.get_text(strip=True)}: {val.get_text(' ', strip=True)}")
    desc = soup.select_one(".description__text, .show-more-less-html__markup")
    if desc:
        bits.append("\nDescription:\n" + desc.get_text("\n", strip=True))
    text = "\n".join(bits).strip()
    return text if len(text) > _MIN_TEXT else None


# --------------------------------------------------------------------------- #
# SEEK / JobStreet GraphQL (the HTML pages are Cloudflare-gated; the API is not)
# --------------------------------------------------------------------------- #

def _seek_job_id(url: str) -> str | None:
    m = _SEEK_JOB_ID.search(url)
    return m.group(1) if m else None


async def _fetch_seek_graphql(url: str, client: httpx.AsyncClient) -> str | None:
    job_id = _seek_job_id(url)
    host = (urlparse(url).hostname or "").lower()
    brand, country = _SEEK_HOSTS.get(host, ("jobstreet", "SG"))
    if not job_id:
        return None

    try:
        resp = await client.post(
            f"https://{host}/graphql",
            headers={
                "Content-Type": "application/json",
                "seek-request-brand": brand,
                "seek-request-country": country,
            },
            json={"operationName": "jobDetails", "variables": {"jobId": job_id}, "query": _SEEK_QUERY},
        )
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None

    job = (((resp.json() or {}).get("data") or {}).get("jobDetails") or {}).get("job")
    if not job:
        return None

    from bs4 import BeautifulSoup

    lines: list[str] = []
    if job.get("title"):
        lines.append(f"Title: {job['title']}")
    if (job.get("advertiser") or {}).get("name"):
        lines.append(f"Company: {job['advertiser']['name']}")
    if (job.get("location") or {}).get("label"):
        lines.append(f"Location: {job['location']['label']}")
    if (job.get("workTypes") or {}).get("label"):
        lines.append(f"Employment type: {job['workTypes']['label']}")
    if (job.get("salary") or {}).get("label"):
        lines.append(f"Salary: {job['salary']['label']}")
    body = BeautifulSoup(job.get("content") or "", "html.parser").get_text("\n")
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    if body:
        lines.append("\nDescription:\n" + body)
    text = "\n".join(lines).strip()
    return text if len(text) > _MIN_TEXT else None


# --------------------------------------------------------------------------- #
# SEEK / JobStreet __NEXT_DATA__
# --------------------------------------------------------------------------- #

def _next_data_text(html: str) -> str | None:
    m = re.search(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None

    found: dict = {}

    def walk(obj) -> None:
        if found:
            return
        if isinstance(obj, dict):
            if obj.get("content") and (obj.get("title") or obj.get("companyName")):
                found["node"] = obj
                return
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    walk(data)
    node = found.get("node")
    if not node:
        return None

    from bs4 import BeautifulSoup

    parts: list[str] = []
    if node.get("title"):
        parts.append(f"Title: {node['title']}")
    if node.get("companyName"):
        parts.append(f"Company: {node['companyName']}")
    loc = node.get("location") or node.get("locationLabel")
    if isinstance(loc, dict):
        loc = loc.get("label") or loc.get("description")
    if loc:
        parts.append(f"Location: {loc}")
    if node.get("workType"):
        parts.append(f"Employment type: {node['workType']}")
    parts.append("\nDescription:\n" + BeautifulSoup(node["content"], "html.parser").get_text("\n"))
    text = "\n".join(parts).strip()
    return text if len(text) > _MIN_TEXT else None


# --------------------------------------------------------------------------- #
# Readable fallback
# --------------------------------------------------------------------------- #

def _extract_main_text(html: str) -> str:
    if not html:
        return ""
    try:
        import trafilatura

        extracted = trafilatura.extract(html, include_comments=False, include_tables=False)
        if extracted:
            return extracted.strip()
    except Exception:  # pragma: no cover
        pass

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "svg"]):
        tag.decompose()
    return re.sub(r"\n{3,}", "\n\n", soup.get_text("\n")).strip()


def _looks_walled(text: str) -> bool:
    low = text.lower()
    if len(text) < _MIN_CHARS:
        return True
    return any(marker in low for marker in _WALL_MARKERS) and len(text) < 2500


# --------------------------------------------------------------------------- #
# Orchestrator
# --------------------------------------------------------------------------- #

async def fetch_posting(url: str, *, timeout: float = 12.0) -> FetchResult:
    platform = detect_platform(url)
    headers = {
        "User-Agent": _UA,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, headers=headers) as client:
        if platform == "linkedin":
            job_id = _linkedin_job_id(url)
            if job_id:
                text = await _fetch_linkedin_guest(job_id, client)
                if text:
                    return FetchResult(platform, text[:24000], False, final_url=url, source="linkedin-guest")

        if platform in {"jobstreet", "seek"}:
            text = await _fetch_seek_graphql(url, client)
            if text:
                return FetchResult(platform, text[:24000], False, final_url=url, source="seek-graphql")

        try:
            resp = await client.get(url)
        except httpx.HTTPError as exc:
            return FetchResult(platform, "", True, reason=f"Could not reach the page ({exc}).")

        html = resp.text if resp.status_code < 400 else ""

        if html:
            node = _jsonld_jobposting(html)
            if node:
                text = _jobposting_to_text(node)
                if len(text) > _MIN_TEXT:
                    return FetchResult(platform, text[:24000], False, final_url=str(resp.url), source="json-ld")
            if platform in {"jobstreet", "seek"}:
                text = _next_data_text(html)
                if text:
                    return FetchResult(platform, text[:24000], False, final_url=str(resp.url), source="next-data")

        if resp.status_code >= 400:
            return FetchResult(
                platform, "", True,
                reason=f"The site returned HTTP {resp.status_code} to an automated request.",
                final_url=str(resp.url),
            )

        text = _extract_main_text(html)
        if _looks_walled(text):
            return FetchResult(
                platform, text, True,
                reason="The posting looks login-gated or is rendered in the browser.",
                final_url=str(resp.url),
            )
        return FetchResult(platform, text[:24000], False, final_url=str(resp.url), source="readable")
