from datetime import datetime, timezone

from app.db.models import ApplicationStatus
from app.services.formatting import (
    format_applied_date,
    format_last_updated,
    format_requirements,
    platform_label,
    status_label,
)


def test_format_requirements_skills_and_experience():
    assert format_requirements(["Python", "Java", "C++"], ["3+ years"]) == "Python, Java, C++ (3+ years)"


def test_format_requirements_skills_only():
    assert format_requirements(["Python"], []) == "Python"


def test_format_requirements_experience_only():
    assert format_requirements([], ["5+ years"]) == "5+ years"


def test_format_requirements_empty():
    assert format_requirements([], []) is None
    assert format_requirements(None, None) is None


def test_status_label_covers_every_status():
    for status in ApplicationStatus:
        label = status_label(status)
        assert label and label[0].isupper()
    assert status_label(ApplicationStatus.in_progress) == "In Progress"


def test_platform_label():
    assert platform_label("linkedin") == "LinkedIn"
    assert platform_label("jobstreet") == "JobStreet"
    assert platform_label(None) == "—"
    assert platform_label("some_ats") == "Some_Ats"


def test_format_applied_date():
    dt = datetime(2026, 9, 12, 3, 4, tzinfo=timezone.utc)
    assert format_applied_date(dt) == "12 Sep 2026"
    assert format_applied_date(None) == ""


def test_format_last_updated():
    dt = datetime(2026, 9, 12, 15, 4, tzinfo=timezone.utc)
    assert format_last_updated(dt) == "03:04 PM 12-09-2026"
    assert format_last_updated(None) == ""
