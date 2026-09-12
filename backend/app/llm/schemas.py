"""Pydantic models for structured LLM output.

``model_json_schema()`` on these feeds the model's ``response_format`` so the
reply is guaranteed to match. Keep every list field a list of short strings —
the product spec wants requirements normalized to tokens like ``Python`` and
``2+ years backend experience``, not prose.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class JobPostingExtraction(BaseModel):
    """Normalized summary of a single job posting."""

    company: str | None = Field(None, description="Hiring company name.")
    title: str | None = Field(None, description="Job title.")
    location: str | None = Field(None, description="Primary location, e.g. 'Singapore' or 'Remote (SEA)'.")
    employment_type: str | None = Field(None, description="e.g. Full-time, Contract, Internship.")
    seniority: str | None = Field(None, description="e.g. Junior, Mid, Senior, Lead.")
    remote_policy: str | None = Field(None, description="e.g. Remote, Hybrid, On-site.")
    salary_text: str | None = Field(None, description="Salary/compensation as stated, else null.")
    skills: list[str] = Field(
        default_factory=list,
        description="Short technical tokens, e.g. ['Python', 'FastAPI', 'PostgreSQL', 'AWS']. No sentences.",
    )
    experience_requirements: list[str] = Field(
        default_factory=list,
        description="Compact phrases, e.g. ['2+ years backend experience', 'REST API design'].",
    )
    education_requirements: list[str] = Field(
        default_factory=list,
        description="Compact phrases, e.g. [\"Bachelor's in CS or equivalent\"]. Empty if not stated.",
    )
    summary: str | None = Field(None, description="2-3 sentence plain-language summary of the role.")


EventTypeLiteral = Literal["applied", "assessment", "interview", "rejection", "offer", "status_update", "other"]


class EmailClassification(BaseModel):
    """Classification + extraction for one email, for the Gmail scan pipeline."""

    job_related: bool = Field(..., description="True only if this is about a specific job application of the user's.")
    event_type: EventTypeLiteral | None = Field(
        None, description="The kind of update, or null if job_related is false."
    )
    company: str | None = Field(None, description="Hiring company, as named in the email.")
    job_title: str | None = Field(None, description="Job title, as named in the email.")
    next_action: str | None = Field(None, description="A short actionable next step, else null.")
    next_action_due: str | None = Field(None, description="ISO date YYYY-MM-DD if a deadline is mentioned, else null.")
    summary: str | None = Field(None, description="One plain-language sentence for the application timeline.")


def strict_schema(model: type[BaseModel]) -> dict:
    """JSON schema with a title and additionalProperties:false everywhere (json_schema strict mode)."""
    schema = model.model_json_schema()
    schema.setdefault("title", model.__name__)

    def _tighten(node: dict) -> None:
        if node.get("type") == "object" or "properties" in node:
            node["additionalProperties"] = False
            node.setdefault("required", list(node.get("properties", {}).keys()))
        for value in node.get("properties", {}).values():
            if isinstance(value, dict):
                _tighten(value)
        for key in ("items", "$defs", "definitions"):
            sub = node.get(key)
            if isinstance(sub, dict):
                if key in ("$defs", "definitions"):
                    for d in sub.values():
                        _tighten(d)
                else:
                    _tighten(sub)

    _tighten(schema)
    return schema
