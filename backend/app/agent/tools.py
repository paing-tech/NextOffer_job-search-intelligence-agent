"""Agent tool specs (OpenAI function-calling format) and their implementations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Application, ApplicationSource, ApplicationStatus
from app.integrations.google_oauth import GoogleNotConnected
from app.services.applications import (
    fields_from_job_posting,
    search_applications,
    serialize_application,
    upsert_application,
)
from app.services.jobs import analyze_job
from app.services.scans import run_scan, serialize_scan_run

TOOL_SPECS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "analyze_job_link",
            "description": "Fetch and summarize a job posting from a URL, or from pasted job-description text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The job posting URL, if the user gave one."},
                    "text": {"type": "string", "description": "Pasted job description text, if the user gave that."},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_applications",
            "description": "List the user's tracked job applications, optionally filtered.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Match against company or job title."},
                    "status": {
                        "type": "string",
                        "enum": [s.value for s in ApplicationStatus],
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_application",
            "description": "Get one tracked application with its event history.",
            "parameters": {
                "type": "object",
                "properties": {"application_id": {"type": "string"}},
                "required": ["application_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "upsert_application",
            "description": "Create or update a tracked application for the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "job_title": {"type": "string"},
                    "status": {"type": "string", "enum": [s.value for s in ApplicationStatus]},
                    "next_action": {"type": "string"},
                    "job_posting_id": {
                        "type": "string",
                        "description": (
                            "The job_posting id from a prior analyze_job_link result, if this application "
                            "is for that posting — fills in salary/requirements/platform automatically."
                        ),
                    },
                },
                "required": ["company", "job_title"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_email_scan",
            "description": (
                "Scan the user's Gmail for job-application updates within a date range and sync them to "
                "the tracker (requires a connected Google account)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "ISO date YYYY-MM-DD to scan from."},
                    "end_date": {
                        "type": "string",
                        "description": "ISO date YYYY-MM-DD to scan through; omit to scan up to today.",
                    },
                },
                "required": ["start_date"],
                "additionalProperties": False,
            },
        },
    },
]


@dataclass
class ToolContext:
    session: AsyncSession
    user_id: uuid.UUID


async def run_tool(name: str, args: dict, ctx: ToolContext) -> dict:
    if name == "analyze_job_link":
        return await analyze_job(
            ctx.session, user_id=ctx.user_id, url=args.get("url"), text=args.get("text")
        )

    if name == "search_applications":
        apps = await search_applications(
            ctx.session, user_id=ctx.user_id, query=args.get("query"), status=args.get("status")
        )
        return {"applications": [serialize_application(a) for a in apps]}

    if name == "get_application":
        try:
            app_id = uuid.UUID(str(args.get("application_id")))
        except ValueError:
            return {"error": "application_id is not a valid id"}
        app = await ctx.session.get(Application, app_id)
        if app is None or app.user_id != ctx.user_id:
            return {"error": "not found"}
        await ctx.session.refresh(app, ["events"])
        return serialize_application(app, include_events=True)

    if name == "upsert_application":
        status = args.get("status")
        posting_id = None
        if args.get("job_posting_id"):
            try:
                posting_id = uuid.UUID(str(args["job_posting_id"]))
            except ValueError:
                posting_id = None
        derived = await fields_from_job_posting(ctx.session, posting_id) if posting_id else {}

        app, created = await upsert_application(
            ctx.session,
            user_id=ctx.user_id,
            company=args["company"],
            job_title=args["job_title"],
            status=ApplicationStatus(status) if status else None,
            source=ApplicationSource.link if posting_id else ApplicationSource.manual,
            next_action=args.get("next_action"),
            job_posting_id=posting_id,
            **derived,
        )
        return {"created": created, "application": serialize_application(app)}

    if name == "run_email_scan":
        try:
            start = date.fromisoformat(args["start_date"])
        except (KeyError, ValueError):
            return {"error": "start_date must be an ISO date (YYYY-MM-DD)."}
        end = None
        if args.get("end_date"):
            try:
                end = date.fromisoformat(args["end_date"])
            except ValueError:
                return {"error": "end_date must be an ISO date (YYYY-MM-DD)."}
        try:
            run = await run_scan(ctx.session, user_id=ctx.user_id, start_date=start, end_date=end)
        except GoogleNotConnected:
            return {"status": "unavailable", "message": "Connect Google in Settings first."}
        return serialize_scan_run(run)

    return {"error": f"unknown tool {name}"}
