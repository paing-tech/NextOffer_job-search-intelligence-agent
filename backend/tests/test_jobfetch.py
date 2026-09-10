from app.integrations.jobfetch import (
    _extract_main_text,
    _jobposting_to_text,
    _jsonld_jobposting,
    _linkedin_job_id,
    _looks_walled,
    _next_data_text,
    _seek_job_id,
    detect_platform,
)


def test_detect_platform():
    assert detect_platform("https://www.linkedin.com/jobs/view/123") == "linkedin"
    assert detect_platform("https://www.jobstreet.com.sg/job/456") == "jobstreet"
    assert detect_platform("https://boards.greenhouse.io/acme/jobs/7") == "greenhouse"
    assert detect_platform("https://careers.acme.dev/roles/7") == "generic"


def test_linkedin_job_id():
    assert _linkedin_job_id("https://www.linkedin.com/jobs/view/3901234567/") == "3901234567"
    assert _linkedin_job_id("https://www.linkedin.com/jobs/search/?currentJobId=3901234567") == "3901234567"
    assert _linkedin_job_id("https://www.linkedin.com/feed/") is None


def test_seek_job_id():
    assert _seek_job_id("https://sg.jobstreet.com/job/94519499?tracking=SHR-IOS") == "94519499"
    assert _seek_job_id("https://www.seek.com.au/job/12345678") == "12345678"
    assert _seek_job_id("https://sg.jobstreet.com/software-engineer-jobs") is None


def test_looks_walled():
    assert _looks_walled("too short") is True
    assert _looks_walled("Sign in to continue. " + "x" * 300) is True
    real = (
        "Backend Engineer at Acme. 3+ years of Python building APIs with FastAPI and "
        "PostgreSQL. You will own services on AWS. " * 6
    )
    assert _looks_walled(real) is False


def test_extract_main_text_strips_markup():
    html = "<html><body><script>bad()</script><h1>Backend Engineer</h1><p>Python, FastAPI</p></body></html>"
    text = _extract_main_text(html)
    assert "Backend Engineer" in text
    assert "bad()" not in text


JSONLD_HTML = """
<html><head>
<script type="application/ld+json">
{"@context":"https://schema.org/","@type":"JobPosting","title":"Senior Backend Engineer",
 "hiringOrganization":{"@type":"Organization","name":"Acme Corp"},
 "jobLocation":{"@type":"Place","address":{"@type":"PostalAddress","addressLocality":"Singapore","addressCountry":"SG"}},
 "employmentType":"FULL_TIME",
 "baseSalary":{"@type":"MonetaryAmount","currency":"SGD","value":{"@type":"QuantitativeValue","minValue":9000,"maxValue":12000,"unitText":"MONTH"}},
 "experienceRequirements":{"@type":"OccupationalExperienceRequirements","monthsOfExperience":36},
 "educationRequirements":{"@type":"EducationalOccupationalCredential","credentialCategory":"bachelor degree"},
 "description":"<p>Build APIs with <b>Python</b>, FastAPI and PostgreSQL. Deploy on AWS.</p>"}
</script></head><body>login wall</body></html>
"""


def test_jsonld_jobposting_parsed_and_rendered():
    node = _jsonld_jobposting(JSONLD_HTML)
    assert node is not None
    text = _jobposting_to_text(node)
    assert "Title: Senior Backend Engineer" in text
    assert "Company: Acme Corp" in text
    assert "Singapore" in text
    assert "3+ years experience" in text
    assert "bachelor degree" in text
    assert "SGD 9000" in text
    assert "Python" in text and "FastAPI" in text


def test_jsonld_jobposting_in_graph():
    html = '<script type="application/ld+json">{"@graph":[{"@type":"WebPage"},{"@type":"JobPosting","title":"X","description":"desc long enough to matter here padding padding"}]}</script>'
    node = _jsonld_jobposting(html)
    assert node and node["title"] == "X"


def test_jsonld_absent_returns_none():
    assert _jsonld_jobposting("<html><body>no structured data</body></html>") is None


def test_next_data_text():
    payload = {
        "props": {"pageProps": {"jobDetails": {
            "title": "Data Engineer", "companyName": "Globex",
            "location": {"label": "Kuala Lumpur"}, "workType": "Full time",
            "content": "<p>Build pipelines with Python and Spark. " + "detail " * 40 + "</p>",
        }}}
    }
    html = f'<script id="__NEXT_DATA__" type="application/json">{__import__("json").dumps(payload)}</script>'
    text = _next_data_text(html)
    assert text and "Title: Data Engineer" in text and "Globex" in text and "Kuala Lumpur" in text
