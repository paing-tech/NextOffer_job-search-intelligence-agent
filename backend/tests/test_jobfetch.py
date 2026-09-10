from app.integrations.jobfetch import _extract_main_text, _looks_walled, detect_platform


def test_detect_platform():
    assert detect_platform("https://www.linkedin.com/jobs/view/123") == "linkedin"
    assert detect_platform("https://www.jobstreet.com.sg/job/456") == "jobstreet"
    assert detect_platform("https://careers.acme.dev/roles/7") == "generic"


def test_looks_walled_thin_content():
    assert _looks_walled("too short") is True


def test_looks_walled_login_marker():
    text = "Sign in to continue. " + "x" * 300
    assert _looks_walled(text) is True


def test_looks_walled_real_posting():
    text = (
        "Backend Engineer at Acme. We are looking for someone with 3+ years of Python experience "
        "building APIs with FastAPI and PostgreSQL. You will own services on AWS. " * 6
    )
    assert _looks_walled(text) is False


def test_extract_main_text_strips_markup():
    html = "<html><body><script>bad()</script><h1>Backend Engineer</h1><p>Python, FastAPI</p></body></html>"
    text = _extract_main_text(html)
    assert "Backend Engineer" in text
    assert "bad()" not in text
