"""Email/password endpoints. The Next.js Credentials provider calls these; the
browser never does directly."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import hash_password, verify_password
from app.db.models import User, UserCredential
from app.db.session import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class UserOut(BaseModel):
    id: str
    email: str


class EmailCheck(BaseModel):
    email: EmailStr


class EmailCheckResult(BaseModel):
    exists: bool
    has_password: bool


@router.post("/exists", response_model=EmailCheckResult)
async def check_email(body: EmailCheck, session: AsyncSession = Depends(get_session)) -> EmailCheckResult:
    """Used by the progressive login form to decide which fields to show next.

    Note: this necessarily reveals whether an email has an account here (the
    same tradeoff Slack/Notion/Linear make for the same UX) — no rate limiting
    yet, acceptable for this project's scale.
    """
    email = body.email.strip().lower()
    user = (await session.scalars(select(User).where(User.email == email))).first()
    if user is None:
        return EmailCheckResult(exists=False, has_password=False)
    cred = await session.get(UserCredential, user.id)
    return EmailCheckResult(exists=True, has_password=cred is not None)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: Credentials, session: AsyncSession = Depends(get_session)) -> UserOut:
    email = body.email.strip().lower()
    exists = (await session.scalars(select(User).where(User.email == email))).first()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with that email already exists.")
    user = User(email=email)
    session.add(user)
    await session.flush()
    session.add(UserCredential(user_id=user.id, password_hash=hash_password(body.password)))
    await session.flush()
    return UserOut(id=str(user.id), email=user.email)


@router.post("/login", response_model=UserOut)
async def login(body: Credentials, session: AsyncSession = Depends(get_session)) -> UserOut:
    email = body.email.strip().lower()
    user = (await session.scalars(select(User).where(User.email == email))).first()
    cred = await session.get(UserCredential, user.id) if user else None
    if not user or not cred or not verify_password(body.password, cred.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")
    return UserOut(id=str(user.id), email=user.email)


class OAuthUpsert(BaseModel):
    email: EmailStr


@router.post("/oauth-upsert", response_model=UserOut)
async def oauth_upsert(body: OAuthUpsert, session: AsyncSession = Depends(get_session)) -> UserOut:
    """Find-or-create a user for an OAuth sign-in (e.g. 'Sign in with Google').

    Called server-side by the Next.js NextAuth config, never by the browser.
    No password is set — an account created this way can't use the email/password
    Credentials flow unless it later sets one. Same email always resolves to the
    same user, whichever way they originally signed up.
    """
    email = body.email.strip().lower()
    user = (await session.scalars(select(User).where(User.email == email))).first()
    if user is None:
        user = User(email=email)
        session.add(user)
        await session.flush()
    return UserOut(id=str(user.id), email=user.email)
