"""Job-link analyzer endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.models import User
from app.db.session import get_session
from app.services.jobs import analyze_job, list_job_postings

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
async def list_postings(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return {"job_postings": await list_job_postings(session, user_id=user.id)}


class AnalyzeRequest(BaseModel):
    url: str | None = None
    text: str | None = None

    @model_validator(mode="after")
    def _one_required(self):
        if not (self.url or self.text):
            raise ValueError("Provide 'url' or 'text'.")
        return self


@router.post("/analyze")
async def analyze(
    body: AnalyzeRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await analyze_job(session, user_id=user.id, url=body.url, text=body.text)
