"""
Per-client WebSocket state.

Tracks which symbols each connected client has subscribed to, and handles
fan-out of tick and alert messages. Calls back into FinnhubStream to keep
upstream refcounts in sync.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from fastapi import WebSocket

if TYPE_CHECKING:
    from .finnhub_stream import FinnhubStream

log = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self, stream: "FinnhubStream") -> None:
        self.stream = stream
        self._clients: dict[WebSocket, set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients[ws] = set()

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            symbols = self._clients.pop(ws, set())
        for symbol in symbols:
            await self.stream.unsubscribe(symbol)

    async def subscribe(self, ws: WebSocket, symbols: list[str]) -> None:
        async with self._lock:
            tracked = self._clients.setdefault(ws, set())
            new = [s.upper() for s in symbols if s.upper() not in tracked]
            tracked.update(new)
        for symbol in new:
            await self.stream.subscribe(symbol)
            # Send the last known price immediately so the UI doesn't wait for the next trade.
            last = self.stream.last_price(symbol)
            if last is not None:
                await self._safe_send(
                    ws,
                    {"type": "tick", "symbol": symbol, "price": last, "ts": 0},
                )

    async def unsubscribe(self, ws: WebSocket, symbols: list[str]) -> None:
        async with self._lock:
            tracked = self._clients.get(ws, set())
            drop = [s.upper() for s in symbols if s.upper() in tracked]
            for s in drop:
                tracked.discard(s)
        for symbol in drop:
            await self.stream.unsubscribe(symbol)

    async def broadcast_tick(self, symbol: str, price: float, ts: int) -> None:
        payload = {"type": "tick", "symbol": symbol, "price": price, "ts": ts}
        async with self._lock:
            targets = [ws for ws, subs in self._clients.items() if symbol in subs]
        for ws in targets:
            await self._safe_send(ws, payload)

    async def broadcast_alert(self, symbol: str, payload: dict) -> None:
        async with self._lock:
            targets = [ws for ws, subs in self._clients.items() if symbol in subs]
        for ws in targets:
            await self._safe_send(ws, payload)

    async def _safe_send(self, ws: WebSocket, payload: dict) -> None:
        try:
            await ws.send_json(payload)
        except Exception as e:
            log.debug("ws send failed, dropping client: %s", e)
            await self.disconnect(ws)
