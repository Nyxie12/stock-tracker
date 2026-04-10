"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db
from .models.user import User
from .utils.security import JWTError, decode_access_token

# auto_error=False so we can implement an "optional" variant using the same scheme.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


_CREDENTIAL_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not token:
        raise _CREDENTIAL_EXC
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise _CREDENTIAL_EXC
    sub = payload.get("sub")
    if sub is None:
        raise _CREDENTIAL_EXC
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise _CREDENTIAL_EXC
    user = await db.get(User, user_id)
    if user is None:
        raise _CREDENTIAL_EXC
    return user


async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if not token:
        return None
    try:
        payload = decode_access_token(token)
    except JWTError:
        return None
    sub = payload.get("sub")
    if sub is None:
        return None
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        return None
    return await db.get(User, user_id)
