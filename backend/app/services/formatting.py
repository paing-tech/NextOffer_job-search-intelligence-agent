"""Display formatting for applications — used by the Sheets sync (the sheet
cells must already contain the final text) and reusable anywhere else that
needs the same 'Saved' / 'LinkedIn' / '12 Sep 2026' style strings."""

from __future__ import annotations

from datetime import datetime

from app.db.models import PLATFORM_LABELS, STATUS_LABELS, ApplicationStatus


def format_requirements(skills: list[str] | None, experience: list[str] | None) -> str | None:
    """'Python, Java, C++ (3+ years)' — skills joined, first experience phrase in parens."""
    parts = [s for s in (skills or []) if s]
    text = ", ".join(parts) if parts else None
    duration = next((e for e in (experience or []) if e), None)
    if text and duration:
        return f"{text} ({duration})"
    return text or duration


def status_label(status: ApplicationStatus) -> str:
    return STATUS_LABELS.get(status, status.value)


def platform_label(platform: str | None) -> str:
    if not platform:
        return "—"
    return PLATFORM_LABELS.get(platform, platform.title())


def format_applied_date(value: datetime | None) -> str:
    return value.strftime("%d %b %Y") if value else ""


def format_last_updated(value: datetime | None) -> str:
    return value.strftime("%I:%M %p %d-%m-%Y") if value else ""
