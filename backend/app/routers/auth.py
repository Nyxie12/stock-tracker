from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import get_current_user
from ..models.paper import PaperPortfolio
from ..models.user import User
from ..models.watchlist import Watchlist
from ..schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut
from ..utils.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _token_for(user: User) -> TokenOut:
    return TokenOut(
        access_token=create_access_token(user.id),
        token_type="bearer",
        user=UserOut(id=user.id, email=user.email),
    )


@router.post("/register", response_model=TokenOut, status_code=201)
async def register(payload: RegisterIn, db: AsyncSession = Depends(get_db)) -> TokenOut:
    email = payload.email.lower().strip()
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    await db.flush()  # populate user.id

    # Seed a default watchlist + paper portfolio so the rest of the app has state to query.
    db.add(Watchlist(user_id=user.id, name="Default"))
    db.add(PaperPortfolio(user_id=user.id, cash=Decimal("100000")))

    await db.commit()
    await db.refresh(user)
    return _token_for(user)


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)) -> TokenOut:
    email = payload.email.lower().strip()
    res = await db.execute(select(User).where(User.email == email))
    user = res.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return _token_for(user)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(id=user.id, email=user.email)
