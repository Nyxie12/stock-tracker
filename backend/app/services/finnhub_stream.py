"""
Finnhub upstream WebSocket bridge.

Responsibilities:
  - Maintain a single upstream connection to wss://ws.finnhub.io.
  - Refcount symbol subscriptions so we only subscribe upstream once per symbol.
  - Throttle per-symbol fan-out: keep the latest tick, flush every TICK_THROTTLE_MS.
  - Maintain a last-price cache used elsewhere (alerts, heatmap, paper P&L).
  - Notify subscribed clients via the ConnectionManager.
  - Auto-reconnect with exponential backoff.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import Counter
from dataclasses import dataclass
from typing import Awaitable, Callable

import websockets

log = logging.getLogger(__name__)

TickCallback = Callable[[str, float, int], Awaitable[None] | None]


@dataclass
class Tick:
    symbol: str
    price: float
    ts: int  # ms since epoch


class FinnhubStream:
    def __init__(self, api_key: str, throttle_ms: int = 500) -> None:
        self.api_key = api_key
        self.throttle_ms = throttle_ms
        self._refcount: Counter[str] = Counter()
        self._last_price: dict[str, float] = {}
        self._pending: dict[str, Tick] = {}
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._run_task: asyncio.Task[None] | None = None
        self._flush_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._subscribers: list[TickCallback] = []
        self._stopping = False

    # ---- lifecycle ------------------------------------------------------

    async def start(self) -> None:
        self._stopping = False
        self._run_task = asyncio.create_task(self._run_loop(), name="finnhub_stream.run")
        self._flush_task = asyncio.create_task(self._flush_loop(), name="finnhub_stream.flush")

    async def stop(self) -> None:
        self._stopping = True
        for task in (self._run_task, self._flush_task):
            if task:
                task.cancel()
        for task in (self._run_task, self._flush_task):
            if task:
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass

    # ---- public API ------------------------------------------------------

    def add_subscriber(self, cb: TickCallback) -> None:
        """Register a coroutine called as cb(symbol, price, ts_ms) on every flushed tick."""
        self._subscribers.append(cb)

    def last_price(self, symbol: str) -> float | None:
        return self._last_price.get(symbol)

    async def subscribe(self, symbol: str) -> None:
        symbol = symbol.upper()
        async with self._lock:
            self._refcount[symbol] += 1
            if self._refcount[symbol] == 1:
                await self._send_upstream({"type": "subscribe", "symbol": symbol})

    async def unsubscribe(self, symbol: str) -> None:
        symbol = symbol.upper()
        async with self._lock:
            if self._refcount[symbol] <= 0:
                return
            self._refcount[symbol] -= 1
            if self._refcount[symbol] == 0:
                del self._refcount[symbol]
                await self._send_upstream({"type": "unsubscribe", "symbol": symbol})

    async def inject(self, symbol: str, price: float) -> None:
        """Debug entry point: synthesize a tick as if it came from upstream."""
        symbol = symbol.upper()
        ts = int(time.time() * 1000)
        self._last_price[symbol] = price
        self._pending[symbol] = Tick(symbol, price, ts)

    # ---- internals ------------------------------------------------------

    async def _send_upstream(self, payload: dict) -> None:
        if self._ws is None:
            return  # will be replayed on reconnect via _resubscribe_all()
        try:
            await self._ws.send(json.dumps(payload))
        except Exception as e:
            log.warning("finnhub send failed: %s", e)

    async def _resubscribe_all(self) -> None:
        for symbol in list(self._refcount):
            await self._send_upstream({"type": "subscribe", "symbol": symbol})

    async def _run_loop(self) -> None:
        backoff = 1.0
        while not self._stopping:
            if not self.api_key:
                log.warning("FINNHUB_API_KEY not set; upstream stream disabled (debug ticks still work)")
                await asyncio.sleep(5)
                continue
            url = f"wss://ws.finnhub.io?token={self.api_key}"
            try:
                async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
                    self._ws = ws
                    log.info("finnhub connected")
                    backoff = 1.0
                    await self._resubscribe_all()
                    async for raw in ws:
                        self._handle_raw(raw)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.warning("finnhub connection error: %s", e)
            finally:
                self._ws = None
            if self._stopping:
                return
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30.0)

    def _handle_raw(self, raw: str | bytes) -> None:
        try:
            if isinstance(raw, bytes):
                raw = raw.decode()
            msg = json.loads(raw)
        except Exception:
            return
        if msg.get("type") != "trade":
            return
        for trade in msg.get("data", []) or []:
            s = trade.get("s")
            p = trade.get("p")
            t = trade.get("t")
            if s is None or p is None:
                continue
            ts = int(t) if t is not None else int(time.time() * 1000)
            self._last_price[s] = float(p)
            # debounce: keep only the latest pending tick per symbol
            self._pending[s] = Tick(symbol=s, price=float(p), ts=ts)

    async def _flush_loop(self) -> None:
        interval = max(self.throttle_ms, 50) / 1000.0
        while not self._stopping:
            try:
                await asyncio.sleep(interval)
                if not self._pending:
                    continue
                batch = self._pending
                self._pending = {}
                for tick in batch.values():
                    for cb in self._subscribers:
                        try:
                            result = cb(tick.symbol, tick.price, tick.ts)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception as e:
                            log.exception("subscriber error: %s", e)
            except asyncio.CancelledError:
                return
            except Exception as e:
                log.exception("flush loop error: %s", e)
