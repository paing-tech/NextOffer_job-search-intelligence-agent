from app.llm.schemas import JobPostingExtraction, strict_schema


def test_strict_schema_is_closed_and_fully_required():
    schema = strict_schema(JobPostingExtraction)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"].keys())
    assert "skills" in schema["properties"]


def test_job_posting_extraction_defaults():
    parsed = JobPostingExtraction.model_validate({"company": "Acme", "skills": ["Python", "FastAPI"]})
    assert parsed.company == "Acme"
    assert parsed.education_requirements == []
    assert parsed.title is None
