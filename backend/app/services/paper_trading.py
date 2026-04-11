"""
Paper trading service.

Pure buy/sell math with weighted-average cost. All money/quantity values are
Decimal on the way in and out. Raises ValueError on any validation failure
(the router translates those to HTTP 400/409).

Rules:
  - Buy: buying power (cash minus pending settlements minus open buy-limit
    reservations) must cover cost. New avg_cost is weighted by
    (old_qty*old_avg + new_qty*price) / total_qty.
  - Sell: quantity must not exceed the current position minus the qty already
    reserved by open sell limits. Sell does NOT change avg_cost. Cash increases
    immediately, but the proceeds are added as a SettlementEvent that settles
    one hour later — so they're visible in `cash` but not in `buying_power`.
  - Realized P&L is computed on each sell and accumulates on the portfolio
    plus is stamped on the trade row.
  - Both buy() and sell() reject when the US market is closed (extended hours
    allowed). The check is *not* bypassed by DEBUG.

All operations are scoped to a single PaperPortfolio passed in by the caller
(one portfolio per user — the auth layer resolves which one).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.paper import (
    LimitOrder,
    PaperPortfolio,
    PaperPosition,
    PaperTrade,
    SettlementEvent,
)
from ..utils.market_hours import is_market_open, market_status

if TYPE_CHECKING:
    from .finnhub_client import FinnhubClient
    from .finnhub_stream import FinnhubStream


SETTLEMENT_DELAY = timedelta(hours=1)
INITIAL_CASH = Decimal("100000")

# Per-process prev-close cache so portfolio_view doesn't hammer Finnhub.
# {symbol: (date_iso, prev_close)}
_PREV_CLOSE_CACHE: dict[str, tuple[str, float]] = {}


async def get_portfolio_for_user(db: AsyncSession, user_id: int) -> PaperPortfolio:
    res = await db.execute(select(PaperPortfolio).where(PaperPortfolio.user_id == user_id))
    p = res.scalar_one_or_none()
    if p is None:
        p = PaperPortfolio(user_id=user_id, cash=INITIAL_CASH, realized_pnl=Decimal("0"))
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


async def _get_live_price(
    stream: "FinnhubStream", finnhub: "FinnhubClient | None", symbol: str
) -> Decimal:
    last = stream.last_price(symbol)
    if last is not None:
        return Decimal(str(last))
    if finnhub is not None:
        quote = await finnhub.quote(symbol)
        if quote.get("c"):
            return Decimal(str(quote["c"]))
    raise ValueError(f"no live price known for {symbol} yet")


async def _purge_settled(db: AsyncSession, portfolio_id: int) -> None:
    """Delete settlement rows whose timer has elapsed. Cheap; runs lazily on
    every buying-power / portfolio-view call."""
    now = datetime.utcnow()
    await db.execute(
        delete(SettlementEvent).where(
            SettlementEvent.portfolio_id == portfolio_id,
            SettlementEvent.settles_at <= now,
        )
    )


async def compute_buying_power(
    db: AsyncSession, portfolio: PaperPortfolio
) -> tuple[Decimal, Decimal, Decimal]:
    """Returns (buying_power, pending_settlement, reserved_for_buy_limits)."""
    await _purge_settled(db, portfolio.id)
    pending = await db.scalar(
        select(func.coalesce(func.sum(SettlementEvent.amount), 0))
        .where(SettlementEvent.portfolio_id == portfolio.id)
        .where(SettlementEvent.settles_at > datetime.utcnow())
    ) or Decimal("0")
    pending = Decimal(str(pending))

    # Buy-limit reservations (qty * limit_price for each open buy limit).
    reserved_q = await db.execute(
        select(LimitOrder).where(
            LimitOrder.portfolio_id == portfolio.id,
            LimitOrder.status == "open",
            LimitOrder.side == "buy",
        )
    )
    reserved = Decimal("0")
    for o in reserved_q.scalars().all():
        reserved += Decimal(o.quantity) * o.limit_price

    buying_power = portfolio.cash - pending - reserved
    if buying_power < 0:
        buying_power = Decimal("0")
    return buying_power, pending, reserved


async def _get_pending_settlements(
    db: AsyncSession, portfolio_id: int
) -> list[SettlementEvent]:
    res = await db.execute(
        select(SettlementEvent)
        .where(
            SettlementEvent.portfolio_id == portfolio_id,
            SettlementEvent.settles_at > datetime.utcnow(),
        )
        .order_by(SettlementEvent.settles_at)
    )
    return list(res.scalars().all())


async def _sell_reserved_qty(db: AsyncSession, portfolio_id: int, symbol: str) -> int:
    """Sum of quantities tied up in open sell-limit orders for this symbol."""
    total = await db.scalar(
        select(func.coalesce(func.sum(LimitOrder.quantity), 0)).where(
            LimitOrder.portfolio_id == portfolio_id,
            LimitOrder.symbol == symbol,
            LimitOrder.side == "sell",
            LimitOrder.status == "open",
        )
    )
    return int(total or 0)


async def buy(
    db: AsyncSession,
    stream: "FinnhubStream",
    finnhub: "FinnhubClient | None",
    portfolio: PaperPortfolio,
    symbol: str,
    quantity: int,
    *,
    skip_market_check: bool = False,
    skip_buying_power_check: bool = False,
) -> PaperTrade:
    if quantity <= 0:
        raise ValueError("quantity must be > 0")
    if not skip_market_check and not is_market_open():
        raise ValueError("Market is closed")
    symbol = symbol.upper()
    price = await _get_live_price(stream, finnhub, symbol)
    cost = price * Decimal(quantity)

    if not skip_buying_power_check:
        buying_power, pending, _ = await compute_buying_power(db, portfolio)
        if buying_power < cost:
            if portfolio.cash >= cost and pending > 0:
                raise ValueError(
                    f"insufficient buying power: funds still settling "
                    f"(${pending} pending). Buying power ${buying_power}, need ${cost}"
                )
            raise ValueError(f"insufficient cash: need {cost}, have {buying_power}")

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
        realized_pnl=None,
    )
    db.add(trade)
    await db.commit()
    await db.refresh(trade)
    return trade


async def sell(
    db: AsyncSession,
    stream: "FinnhubStream",
    finnhub: "FinnhubClient | None",
    portfolio: PaperPortfolio,
    symbol: str,
    quantity: int,
    *,
    skip_market_check: bool = False,
    skip_reservation_check: bool = False,
) -> PaperTrade:
    if quantity <= 0:
        raise ValueError("quantity must be > 0")
    if not skip_market_check and not is_market_open():
        raise ValueError("Market is closed")
    symbol = symbol.upper()
    position = await _get_position(db, portfolio.id, symbol)
    if position is None:
        raise ValueError(f"insufficient position: need {quantity}, have 0")

    available = position.quantity
    if not skip_reservation_check:
        available -= await _sell_reserved_qty(db, portfolio.id, symbol)
    if available < quantity:
        raise ValueError(
            f"insufficient position: need {quantity}, have {available} (after reservations)"
        )

    price = await _get_live_price(stream, finnhub, symbol)
    proceeds = price * Decimal(quantity)
    realized = (price - position.avg_cost) * Decimal(quantity)

    portfolio.cash += proceeds
    portfolio.realized_pnl = (portfolio.realized_pnl or Decimal("0")) + realized

    settlement = SettlementEvent(
        portfolio_id=portfolio.id,
        amount=proceeds,
        settles_at=datetime.utcnow() + SETTLEMENT_DELAY,
    )
    db.add(settlement)

    position.quantity -= quantity
    if position.quantity == 0:
        await db.delete(position)

    trade = PaperTrade(
        portfolio_id=portfolio.id,
        symbol=symbol,
        side="sell",
        quantity=quantity,
        price=price,
        realized_pnl=realized,
    )
    db.add(trade)
    await db.commit()
    await db.refresh(trade)
    return trade


async def reset_portfolio(db: AsyncSession, portfolio: PaperPortfolio) -> PaperPortfolio:
    """Wipe positions, trades, settlements, and limit orders. Reset cash."""
    await db.execute(
        delete(PaperPosition).where(PaperPosition.portfolio_id == portfolio.id)
    )
    await db.execute(
        delete(PaperTrade).where(PaperTrade.portfolio_id == portfolio.id)
    )
    await db.execute(
        delete(SettlementEvent).where(SettlementEvent.portfolio_id == portfolio.id)
    )
    await db.execute(
        delete(LimitOrder).where(LimitOrder.portfolio_id == portfolio.id)
    )
    portfolio.cash = INITIAL_CASH
    portfolio.realized_pnl = Decimal("0")
    await db.commit()
    await db.refresh(portfolio)
    return portfolio


async def _prev_close_for(
    finnhub: "FinnhubClient | None", symbol: str
) -> float | None:
    today = datetime.utcnow().date().isoformat()
    cached = _PREV_CLOSE_CACHE.get(symbol)
    if cached and cached[0] == today:
        return cached[1]
    if finnhub is None:
        return None
    try:
        q = await finnhub.quote(symbol)
    except Exception:
        return None
    pc = q.get("pc") if q else None
    if pc:
        _PREV_CLOSE_CACHE[symbol] = (today, float(pc))
        return float(pc)
    return None


async def portfolio_view(
    db: AsyncSession,
    stream: "FinnhubStream",
    finnhub: "FinnhubClient | None",
    portfolio: PaperPortfolio,
) -> dict:
    res = await db.execute(
        select(PaperPosition)
        .where(PaperPosition.portfolio_id == portfolio.id)
        .order_by(PaperPosition.symbol)
    )
    positions: list[dict] = []
    market_value = Decimal(0)
    for p in res.scalars().all():
        last = stream.last_price(p.symbol)
        if last is None and finnhub is not None:
            quote = await finnhub.quote(p.symbol)
            if quote and quote.get("c"):
                last = quote["c"]

        prev_close = await _prev_close_for(finnhub, p.symbol)

        mv = None
        unrl = None
        unrl_pct = None
        day_change = None
        day_change_pct = None
        if last is not None:
            last_d = Decimal(str(last))
            mv = last_d * Decimal(p.quantity)
            unrl = (last_d - p.avg_cost) * Decimal(p.quantity)
            if p.avg_cost > 0:
                unrl_pct = float((last_d - p.avg_cost) / p.avg_cost * Decimal(100))
            market_value += mv
            if prev_close and prev_close > 0:
                day_change = (float(last) - prev_close) * p.quantity
                day_change_pct = (float(last) - prev_close) / prev_close * 100.0

        positions.append(
            {
                "symbol": p.symbol,
                "quantity": p.quantity,
                "avg_cost": float(p.avg_cost),
                "last_price": float(last) if last is not None else None,
                "prev_close": prev_close,
                "market_value": float(mv) if mv is not None else None,
                "unrealized_pnl": float(unrl) if unrl is not None else None,
                "unrealized_pnl_pct": unrl_pct,
                "day_change": day_change,
                "day_change_pct": day_change_pct,
            }
        )

    buying_power, pending, reserved = await compute_buying_power(db, portfolio)
    pending_rows = await _get_pending_settlements(db, portfolio.id)

    total = portfolio.cash + market_value
    return {
        "cash": float(portfolio.cash),
        "buying_power": float(buying_power),
        "pending_settlement": float(pending),
        "reserved_for_orders": float(reserved),
        "pending_settlements": [
            {"amount": float(s.amount), "settles_at": s.settles_at.isoformat()}
            for s in pending_rows
        ],
        "positions": positions,
        "market_value": float(market_value),
        "total_value": float(total),
        "initial_cash": float(INITIAL_CASH),
        "realized_pnl": float(portfolio.realized_pnl or Decimal("0")),
        "market_status": market_status(),
    }


# ─── Limit orders ───────────────────────────────────────────────────────────


async def place_limit_order(
    db: AsyncSession,
    portfolio: PaperPortfolio,
    symbol: str,
    side: str,
    quantity: int,
    limit_price: Decimal,
) -> LimitOrder:
    if quantity <= 0:
        raise ValueError("quantity must be > 0")
    if limit_price <= 0:
        raise ValueError("limit_price must be > 0")
    if side not in ("buy", "sell"):
        raise ValueError("side must be 'buy' or 'sell'")

    symbol = symbol.upper()

    if side == "buy":
        cost = Decimal(quantity) * limit_price
        buying_power, _, _ = await compute_buying_power(db, portfolio)
        if buying_power < cost:
            raise ValueError(
                f"insufficient buying power for limit order: need {cost}, have {buying_power}"
            )
    else:
        position = await _get_position(db, portfolio.id, symbol)
        held = position.quantity if position else 0
        already_reserved = await _sell_reserved_qty(db, portfolio.id, symbol)
        if held - already_reserved < quantity:
            raise ValueError(
                f"insufficient position to reserve: need {quantity}, "
                f"have {held - already_reserved} unreserved"
            )

    order = LimitOrder(
        portfolio_id=portfolio.id,
        symbol=symbol,
        side=side,
        quantity=quantity,
        limit_price=limit_price,
        status="open",
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


async def cancel_limit_order(
    db: AsyncSession, portfolio: PaperPortfolio, order_id: int
) -> LimitOrder:
    order = await db.get(LimitOrder, order_id)
    if order is None or order.portfolio_id != portfolio.id:
        raise ValueError("order not found")
    if order.status != "open":
        raise ValueError(f"order is not open (status={order.status})")
    order.status = "cancelled"
    await db.commit()
    await db.refresh(order)
    return order


async def list_limit_orders(
    db: AsyncSession, portfolio: PaperPortfolio, status: str | None = "open"
) -> list[LimitOrder]:
    stmt = select(LimitOrder).where(LimitOrder.portfolio_id == portfolio.id)
    if status:
        stmt = stmt.where(LimitOrder.status == status)
    stmt = stmt.order_by(LimitOrder.created_at.desc())
    res = await db.execute(stmt)
    return list(res.scalars().all())
