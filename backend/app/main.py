"""NextOffer API — job-search intelligence agent.

Milestone 0: auth, job-link analyzer, chat agent, application tracking.
Google (Gmail + Sheets), the email-scan pipeline, and scheduled automatic
scans (milestone 3) are live too.
"""

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import applications, auth, chat, google, jobs, scans
from app.services.auto_scan import auto_scan_loop

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # One background task for the whole process (not per-request) that polls
    # for due automatic scans — see app.services.auto_scan.
    task = asyncio.create_task(auto_scan_loop(settings.auto_scan_poll_seconds))
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="NextOffer API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(chat.router)
app.include_router(applications.router)
app.include_router(google.router)
app.include_router(scans.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "nextoffer-api"}
