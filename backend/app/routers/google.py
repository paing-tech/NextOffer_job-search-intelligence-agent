"""Google connection endpoints — stubbed until milestone 1 (OAuth + Gmail + Sheets)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.deps import get_current_user
from app.db.models import User

router = APIRouter(prefix="/google", tags=["google"])

_NOT_YET = "Google OAuth (Gmail + Sheets) is implemented in milestone 1."


@router.get("/status")
async def connection_status(user: User = Depends(get_current_user)) -> dict:
    return {"connected": False, "message": _NOT_YET}


@router.get("/authorize")
async def authorize(user: User = Depends(get_current_user)) -> dict:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, _NOT_YET)


@router.get("/callback")
async def callback() -> dict:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, _NOT_YET)


@router.delete("/connection")
async def disconnect(user: User = Depends(get_current_user)) -> dict:
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, _NOT_YET)
