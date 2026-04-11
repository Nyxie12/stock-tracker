from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import get_current_user
from ..models.paper import LimitOrder, PaperTrade
from ..models.user import User
from ..schemas.paper import (
    LimitOrderIn,
    LimitOrderOut,
    MarketStatusOut,
    PortfolioOut,
    TradeIn,
    TradeOut,
)
from ..services import paper_trading
from ..utils.market_hours import market_status

router = APIRouter(prefix="/api/paper", tags=["paper"])


def _trade_error(e: ValueError) -> HTTPException:
    msg = str(e)
    # 409 = state conflict (market closed, insufficient funds, etc.)
    if any(
        s in msg
        for s in (
            "Market is closed",
            "insufficient cash",
            "insufficient buying power",
            "insufficient position",
            "still settling",
        )
    ):
        return HTTPException(409, msg)
    return HTTPException(400, msg)


@router.get("/market-status", response_model=MarketStatusOut)
async def market_status_endpoint() -> dict:
    return market_status()


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
            db,
            request.app.state.stream,
            request.app.state.finnhub,
            p,
            payload.symbol,
            payload.quantity,
        )
    except ValueError as e:
        raise _trade_error(e)


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
            db,
            request.app.state.stream,
            request.app.state.finnhub,
            p,
            payload.symbol,
            payload.quantity,
        )
    except ValueError as e:
        raise _trade_error(e)


@router.post("/reset", response_model=PortfolioOut)
async def reset(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    p = await paper_trading.get_portfolio_for_user(db, user.id)
    # Drop any in-memory limit orders for this portfolio before wiping the rows.
    engine = getattr(request.app.state, "limit_order_engine", None)
    if engine is not None:
        for orders in list(engine._by_symbol.values()):
            for o in list(orders):
                if o.portfolio_id == p.id:
                    await engine.remove(o.id)
    await paper_trading.reset_portfolio(db, p)
    return await paper_trading.portfolio_view(
        db, request.app.state.stream, request.app.state.finnhub, p
    )


# ─── Limit orders ──────────────────────────────────────────────────────────


@router.get("/orders", response_model=list[LimitOrderOut])
async def list_orders(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[LimitOrder]:
    p = await paper_trading.get_portfolio_for_user(db, user.id)
    return await paper_trading.list_limit_orders(db, p, status="open")


@router.post("/orders", response_model=LimitOrderOut, status_code=201)
async def place_order(
    payload: LimitOrderIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LimitOrder:
    p = await paper_trading.get_portfolio_for_user(db, user.id)
    try:
        order = await paper_trading.place_limit_order(
            db,
            p,
            payload.symbol,
            payload.side,
            payload.quantity,
            Decimal(str(payload.limit_price)),
        )
    except ValueError as e:
        raise _trade_error(e)

    engine = getattr(request.app.state, "limit_order_engine", None)
    if engine is not None:
        await engine.add(order, user_id=user.id)
    return order


@router.delete("/orders/{order_id}", response_model=LimitOrderOut)
async def cancel_order(
    order_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LimitOrder:
    p = await paper_trading.get_portfolio_for_user(db, user.id)
    try:
        order = await paper_trading.cancel_limit_order(db, p, order_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    engine = getattr(request.app.state, "limit_order_engine", None)
    if engine is not None:
        await engine.remove(order_id)
    return order
