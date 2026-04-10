from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import get_current_user
from ..models.paper import PaperTrade
from ..models.user import User
from ..schemas.paper import PortfolioOut, TradeIn, TradeOut
from ..services import paper_trading

router = APIRouter(prefix="/api/paper", tags=["paper"])


@router.get("/portfolio", response_model=PortfolioOut)
async def portfolio(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    p = await paper_trading.get_portfolio_for_user(db, user.id)
    return await paper_trading.portfolio_view(
        db, request.app.state.stream, request.app.state.finnhub, p
    )


@router.get("/trades", response_model=list[TradeOut])
async def list_trades(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PaperTrade]:
    p = await paper_trading.get_portfolio_for_user(db, user.id)
    res = await db.execute(
        select(PaperTrade)
        .where(PaperTrade.portfolio_id == p.id)
        .order_by(PaperTrade.executed_at.desc())
    )
    return list(res.scalars().all())


@router.post("/buy", response_model=TradeOut, status_code=201)
async def buy(
    payload: TradeIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PaperTrade:
    p = await paper_trading.get_portfolio_for_user(db, user.id)
    try:
        return await paper_trading.buy(
            db, request.app.state.stream, request.app.state.finnhub, p, payload.symbol, payload.quantity
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/sell", response_model=TradeOut, status_code=201)
async def sell(
    payload: TradeIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PaperTrade:
    p = await paper_trading.get_portfolio_for_user(db, user.id)
    try:
        return await paper_trading.sell(
            db, request.app.state.stream, request.app.state.finnhub, p, payload.symbol, payload.quantity
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
