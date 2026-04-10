"""
Alert engine.

Detects threshold *crossings* (not instantaneous violations) so an alert fires
once per crossing instead of spamming every tick while the price stays past
the threshold.

Algorithm: for each tick, compare the new price against the previous price we
saw for that symbol. A crossing has occurred when:
  - condition "above": prev < threshold <= new
  - condition "below": prev > threshold >= new

The first tick after startup establishes a baseline and does not fire.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..models.alert import Alert

if TYPE_CHECKING:
    from .connection_manager import ConnectionManager
    from .finnhub_stream import FinnhubStream

log = logging.getLogger(__name__)


@dataclass
class _LoadedAlert:
    id: int
    user_id: int
    symbol: str
    condition: str
    threshold: float
    active: bool


class AlertEngine:
    def __init__(
        self,
        session_factory: async_sessionmaker,
        stream: "FinnhubStream",
        manager: "ConnectionManager",
    ) -> None:
        self.session_factory = session_factory
        self.stream = stream
        self.manager = manager
        self._by_symbol: dict[str, list[_LoadedAlert]] = {}
        self._prev_price: dict[str, float] = {}

    async def load_from_db(self) -> None:
        self._by_symbol.clear()
        async with self.session_factory() as db:
            res = await db.execute(select(Alert).where(Alert.active.is_(True)))
            for a in res.scalars().all():
                self._by_symbol.setdefault(a.symbol, []).append(
                    _LoadedAlert(
                        id=a.id,
                        user_id=a.user_id,
                        symbol=a.symbol,
                        condition=a.condition,
                        threshold=float(a.threshold),
                        active=True,
                    )
                )
        # Ensure upstream subscription for every alert symbol.
        for symbol in self._by_symbol:
            await self.stream.subscribe(symbol)

    async def add(self, alert: Alert) -> None:
        self._by_symbol.setdefault(alert.symbol, []).append(
            _LoadedAlert(
                id=alert.id,
                user_id=alert.user_id,
                symbol=alert.symbol,
                condition=alert.condition,
                threshold=float(alert.threshold),
                active=alert.active,
            )
        )
        if alert.active:
            await self.stream.subscribe(alert.symbol)

    async def remove(self, alert_id: int) -> None:
        for symbol, alerts in list(self._by_symbol.items()):
            before = len(alerts)
            self._by_symbol[symbol] = [a for a in alerts if a.id != alert_id]
            after = len(self._by_symbol[symbol])
            if after == 0:
                del self._by_symbol[symbol]
                await self.stream.unsubscribe(symbol)
            elif after < before:
                # we dropped this alert's hold on the symbol
                await self.stream.unsubscribe(symbol)

    async def set_active(self, alert_id: int, active: bool) -> None:
        for alerts in self._by_symbol.values():
            for a in alerts:
                if a.id == alert_id and a.active != active:
                    a.active = active
                    if active:
                        await self.stream.subscribe(a.symbol)
                    else:
                        await self.stream.unsubscribe(a.symbol)
                    return

    async def on_tick(self, symbol: str, price: float, ts: int) -> None:
        alerts = self._by_symbol.get(symbol)
        prev = self._prev_price.get(symbol)
        self._prev_price[symbol] = price
        if not alerts or prev is None:
            return
        for a in alerts:
            if not a.active:
                continue
            crossed = False
            if a.condition == "above" and prev < a.threshold <= price:
                crossed = True
            elif a.condition == "below" and prev > a.threshold >= price:
                crossed = True
            if crossed:
                await self._fire(a, price, ts)

    async def _fire(self, a: _LoadedAlert, price: float, ts: int) -> None:
        log.info("alert fired id=%s %s %s %.4f @ %.4f", a.id, a.symbol, a.condition, a.threshold, price)
        now = datetime.utcnow()
        try:
            async with self.session_factory() as db:
                row = await db.get(Alert, a.id)
                if row:
                    row.last_triggered_at = now
                    await db.commit()
        except Exception as e:
            log.warning("failed to persist alert fire: %s", e)
        await self.manager.broadcast_to_user(
            a.user_id,
            {
                "type": "alert",
                "alertId": a.id,
                "symbol": a.symbol,
                "condition": a.condition,
                "threshold": a.threshold,
                "price": price,
                "ts": ts,
            },
        )
