"""
Limit order fill engine.

Mirrors `alert_engine.py` in structure: holds an in-memory `{symbol: [orders]}`
index keyed by symbol, and is fed by the same tick fan-out in `main.py`.

Fill rules:
  - buy limit fills when tick price <= limit_price
  - sell limit fills when tick price >= limit_price
  - only fills during market hours (extended hours allowed)

When an order fills, the engine calls into `paper_trading.buy/sell` with
`skip_market_check=True` (already checked) and `skip_buying_power_check=True`
or `skip_reservation_check=True` (resources were already reserved at placement).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..models.paper import LimitOrder, PaperPortfolio
from ..utils.market_hours import is_market_open
from . import paper_trading

if TYPE_CHECKING:
    from .connection_manager import ConnectionManager
    from .finnhub_client import FinnhubClient
    from .finnhub_stream import FinnhubStream

log = logging.getLogger(__name__)


@dataclass
class _LoadedOrder:
    id: int
    portfolio_id: int
    user_id: int
    symbol: str
    side: str
    quantity: int
    limit_price: float


class LimitOrderEngine:
    def __init__(
        self,
        session_factory: async_sessionmaker,
        stream: "FinnhubStream",
        finnhub: "FinnhubClient | None",
        manager: "ConnectionManager",
    ) -> None:
        self.session_factory = session_factory
        self.stream = stream
        self.finnhub = finnhub
        self.manager = manager
        self._by_symbol: dict[str, list[_LoadedOrder]] = {}

    async def load_from_db(self) -> None:
        self._by_symbol.clear()
        async with self.session_factory() as db:
            res = await db.execute(
                select(LimitOrder, PaperPortfolio.user_id)
                .join(PaperPortfolio, PaperPortfolio.id == LimitOrder.portfolio_id)
                .where(LimitOrder.status == "open")
            )
            for o, user_id in res.all():
                self._by_symbol.setdefault(o.symbol, []).append(
                    _LoadedOrder(
                        id=o.id,
                        portfolio_id=o.portfolio_id,
                        user_id=user_id,
                        symbol=o.symbol,
                        side=o.side,
                        quantity=o.quantity,
                        limit_price=float(o.limit_price),
                    )
                )
        for symbol in self._by_symbol:
            await self.stream.subscribe(symbol)

    async def add(self, order: LimitOrder, user_id: int) -> None:
        self._by_symbol.setdefault(order.symbol, []).append(
            _LoadedOrder(
                id=order.id,
                portfolio_id=order.portfolio_id,
                user_id=user_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                limit_price=float(order.limit_price),
            )
        )
        await self.stream.subscribe(order.symbol)

    async def remove(self, order_id: int) -> None:
        for symbol, orders in list(self._by_symbol.items()):
            kept = [o for o in orders if o.id != order_id]
            if len(kept) != len(orders):
                if kept:
                    self._by_symbol[symbol] = kept
                else:
                    del self._by_symbol[symbol]
                    await self.stream.unsubscribe(symbol)
                return

    async def on_tick(self, symbol: str, price: float, ts: int) -> None:
        if not is_market_open():
            return
        orders = self._by_symbol.get(symbol)
        if not orders:
            return
        to_fill: list[_LoadedOrder] = []
        for o in orders:
            if o.side == "buy" and price <= o.limit_price:
                to_fill.append(o)
            elif o.side == "sell" and price >= o.limit_price:
                to_fill.append(o)
        for o in to_fill:
            await self._fill(o, price, ts)

    async def _fill(self, o: _LoadedOrder, price: float, ts: int) -> None:
        log.info(
            "limit order fill id=%s %s %s %s @ %.4f (limit=%.4f)",
            o.id, o.side, o.quantity, o.symbol, price, o.limit_price,
        )
        try:
            async with self.session_factory() as db:
                row = await db.get(LimitOrder, o.id)
                if row is None or row.status != "open":
                    await self.remove(o.id)
                    return
                portfolio = await db.get(PaperPortfolio, row.portfolio_id)
                if portfolio is None:
                    return
                # Mark filled BEFORE executing the trade so the reservation
                # release doesn't double-count this order.
                row.status = "filled"
                row.filled_at = datetime.utcnow()
                await db.commit()
                try:
                    if o.side == "buy":
                        await paper_trading.buy(
                            db,
                            self.stream,
                            self.finnhub,
                            portfolio,
                            o.symbol,
                            o.quantity,
                            skip_market_check=True,
                            skip_buying_power_check=True,
                        )
                    else:
                        await paper_trading.sell(
                            db,
                            self.stream,
                            self.finnhub,
                            portfolio,
                            o.symbol,
                            o.quantity,
                            skip_market_check=True,
                            skip_reservation_check=True,
                        )
                except Exception as e:
                    log.warning("limit fill execution failed for order %s: %s", o.id, e)
                    row.status = "open"
                    row.filled_at = None
                    await db.commit()
                    return
        except Exception as e:
            log.warning("limit fill failed id=%s: %s", o.id, e)
            return

        await self.remove(o.id)
        await self.manager.broadcast_to_user(
            o.user_id,
            {
                "type": "limit_order_filled",
                "orderId": o.id,
                "symbol": o.symbol,
                "side": o.side,
                "quantity": o.quantity,
                "price": price,
                "ts": ts,
            },
        )
