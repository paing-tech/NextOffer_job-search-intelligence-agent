"""Request auth: verify the short-lived HS256 bearer token minted by the Next.js BFF.

The frontend never exposes the backend to the browser directly; its
``/api/backend/[...path]`` route reads the NextAuth session and signs a token
with the shared ``AUTH_SECRET``. Here we verify it and load the user.
"""

import uuid

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import User
from app.db.session import get_session

_settings = get_settings()


async def get_current_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        claims = jwt.decode(token, _settings.auth_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}") from exc

    sub = claims.get("sub")
    email = (claims.get("email") or "").strip().lower()
    if not sub or not email:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token missing sub/email")

    try:
        user_id = uuid.UUID(str(sub))
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token sub is not a user id") from exc

    user = await session.get(User, user_id)
    if user is None:
        # Fall back to email for a freshly registered user whose id the token predates.
        user = (await session.scalars(select(User).where(User.email == email))).first()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def decode_state_token(token: str) -> uuid.UUID:
    """Verify the short-lived HS256 token used as the Google OAuth `state` param.

    Same shape as the bearer token above (minted by the frontend's
    ``mintBackendToken``), just carried through Google's redirect instead of an
    Authorization header — there is no request the browser sends with a header
    on an OAuth callback, so the state param is how we know which user this is.
    """
    try:
        claims = jwt.decode(token, _settings.auth_secret, algorithms=["HS256"])
        return uuid.UUID(str(claims["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid or expired state: {exc}") from exc
