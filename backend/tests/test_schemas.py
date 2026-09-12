from app.llm.schemas import EmailClassification, JobPostingExtraction, strict_schema


def test_strict_schema_is_closed_and_fully_required():
    schema = strict_schema(JobPostingExtraction)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"].keys())
    assert "skills" in schema["properties"]


def test_strict_schema_required_includes_optional_fields_too():
    # Regression: EmailClassification.job_related has no default, so Pydantic's
    # generated schema already carries a *partial* `required` list containing
    # just that field — the tightening step must overwrite it, not skip it.
    schema = strict_schema(EmailClassification)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"].keys())
    assert "event_type" in schema["required"]
    assert "company" in schema["required"]


def test_job_posting_extraction_defaults():
    parsed = JobPostingExtraction.model_validate({"company": "Acme", "skills": ["Python", "FastAPI"]})
    assert parsed.company == "Acme"
    assert parsed.education_requirements == []
    assert parsed.title is None
