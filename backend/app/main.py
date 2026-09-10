"""NextOffer API — job-search intelligence agent.

Milestone 0: auth, job-link analyzer, chat agent, application tracking.
Google (Gmail + Sheets) and the email-scan pipeline follow in milestones 1-2.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import applications, auth, chat, google, jobs, scans

settings = get_settings()

app = FastAPI(title="NextOffer API", version="0.2.0")

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
