"""
Paper trading service.

Pure buy/sell math with weighted-average cost. All money/quantity values are
Decimal on the way in and out. Raises ValueError on any validation failure
(the router translates those to HTTP 400).

Rules:
  - Buy: cash must be sufficient at the given price; new avg_cost is
    weighted by (old_qty*old_avg + new_qty*price) / total_qty.
  - Sell: quantity must not exceed the current position; sell does NOT
    change avg_cost; cash increases by qty*price; when position hits 0
    it is removed from the DB.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.paper import PaperPortfolio, PaperPosition, PaperTrade

if TYPE_CHECKING:
    from .finnhub_stream import FinnhubStream


async def get_or_create_portfolio(db: AsyncSession) -> PaperPortfolio:
    res = await db.execute(select(PaperPortfolio).order_by(PaperPortfolio.id).limit(1))
    p = res.scalar_one_or_none()
    if p is None:
        p = PaperPortfolio(cash=Decimal("100000"))
        db.add(p)
        await db.commit()
        await db.refresh(p)
    return p


async def _get_position(db: AsyncSession, portfolio_id: int, symbol: str) -> PaperPosition | None:
    res = await db.execute(
        select(PaperPosition).where(
            PaperPosition.portfolio_id == portfolio_id, PaperPosition.symbol == symbol
        )
    )
    return res.scalar_one_or_none()


def _price_or_raise(stream: "FinnhubStream", symbol: str) -> Decimal:
    # Deprecated: use async _get_live_price instead
    pass

async def _get_live_price(stream: "FinnhubStream", finnhub: "FinnhubClient", symbol: str) -> Decimal:
    last = stream.last_price(symbol)
    if last is not None:
        return Decimal(str(last))
    quote = await finnhub.quote(symbol)
    if not quote.get("c"):
        raise ValueError(f"no live price known for {symbol} yet")
    return Decimal(str(quote["c"]))


async def buy(
    db: AsyncSession, stream: "FinnhubStream", finnhub: "FinnhubClient", symbol: str, quantity: int
) -> PaperTrade:
    if quantity <= 0:
        raise ValueError("quantity must be > 0")
    symbol = symbol.upper()
    portfolio = await get_or_create_portfolio(db)
    price = await _get_live_price(stream, finnhub, symbol)
    cost = price * Decimal(quantity)
    if portfolio.cash < cost:
        raise ValueError(
            f"insufficient cash: need {cost}, have {portfolio.cash}"
        )
    portfolio.cash -= cost

    position = await _get_position(db, portfolio.id, symbol)
    if position is None:
        position = PaperPosition(
            portfolio_id=portfolio.id, symbol=symbol, quantity=quantity, avg_cost=price
        )
        db.add(position)
    else:
        total_qty = position.quantity + quantity
        new_avg = (
            position.avg_cost * Decimal(position.quantity) + price * Decimal(quantity)
        ) / Decimal(total_qty)
        position.quantity = total_qty
        position.avg_cost = new_avg.quantize(Decimal("0.0001"))

    trade = PaperTrade(
        portfolio_id=portfolio.id,
        symbol=symbol,
        side="buy",
        quantity=quantity,
        price=price,
    )
    db.add(trade)
    await db.commit()
    await db.refresh(trade)
    return trade


async def sell(
    db: AsyncSession, stream: "FinnhubStream", finnhub: "FinnhubClient", symbol: str, quantity: int
) -> PaperTrade:
    if quantity <= 0:
        raise ValueError("quantity must be > 0")
    symbol = symbol.upper()
    portfolio = await get_or_create_portfolio(db)
    position = await _get_position(db, portfolio.id, symbol)
    if position is None or position.quantity < quantity:
        have = position.quantity if position else 0
        raise ValueError(f"insufficient position: need {quantity}, have {have}")
    price = await _get_live_price(stream, finnhub, symbol)
    proceeds = price * Decimal(quantity)
    portfolio.cash += proceeds
    position.quantity -= quantity
    if position.quantity == 0:
        await db.delete(position)

    trade = PaperTrade(
        portfolio_id=portfolio.id,
        symbol=symbol,
        side="sell",
        quantity=quantity,
        price=price,
    )
    db.add(trade)
    await db.commit()
    await db.refresh(trade)
    return trade


async def portfolio_view(db: AsyncSession, stream: "FinnhubStream", finnhub: "FinnhubClient") -> dict:
    portfolio = await get_or_create_portfolio(db)
    res = await db.execute(
        select(PaperPosition).where(PaperPosition.portfolio_id == portfolio.id).order_by(
            PaperPosition.symbol
        )
    )
    positions: list[dict] = []
    market_value = Decimal(0)
    for p in res.scalars().all():
        last = stream.last_price(p.symbol)
        if last is None:
            quote = await finnhub.quote(p.symbol)
            if quote and quote.get("c"):
                last = quote["c"]
        
        mv = None
        unrl = None
        unrl_pct = None
        if last is not None:
            last_d = Decimal(str(last))
            mv = last_d * Decimal(p.quantity)
            unrl = (last_d - p.avg_cost) * Decimal(p.quantity)
            if p.avg_cost > 0:
                unrl_pct = float((last_d - p.avg_cost) / p.avg_cost * Decimal(100))
            market_value += mv
        positions.append(
            {
                "symbol": p.symbol,
                "quantity": p.quantity,
                "avg_cost": float(p.avg_cost),
                "last_price": float(last) if last is not None else None,
                "market_value": float(mv) if mv is not None else None,
                "unrealized_pnl": float(unrl) if unrl is not None else None,
                "unrealized_pnl_pct": unrl_pct,
            }
        )
    total = portfolio.cash + market_value
    return {
        "cash": float(portfolio.cash),
        "positions": positions,
        "market_value": float(market_value),
        "total_value": float(total),
        "initial_cash": 100000.0,
    }
