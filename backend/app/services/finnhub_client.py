"""Thin async wrapper around Finnhub REST endpoints used for non-streaming data."""

from __future__ import annotations

import asyncio
import logging
import time

import httpx

log = logging.getLogger(__name__)

BASE_URL = "https://finnhub.io/api/v1"

# Finnhub free tier: 60 calls/minute.  We stay well under with a simple
# throttle that spaces requests at least _RATE_INTERVAL apart.
_RATE_INTERVAL = 1.0  # 1 request per second → 60/min max


class FinnhubClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=10.0)
        self._profile_cache: dict[str, tuple[float, dict]] = {}
        self._quote_cache: dict[str, tuple[float, dict]] = {}
        self._rate_lock = asyncio.Lock()
        self._last_request_time = 0.0

    async def close(self) -> None:
        await self._client.aclose()

    async def _throttle(self) -> None:
        """Simple token-bucket: ensure at least _RATE_INTERVAL between requests."""
        async with self._rate_lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time
            if elapsed < _RATE_INTERVAL:
                await asyncio.sleep(_RATE_INTERVAL - elapsed)
            self._last_request_time = asyncio.get_event_loop().time()

    async def _get(self, path: str, **params: str) -> dict:
        if not self.api_key:
            return {}
        await self._throttle()
        params["token"] = self.api_key
        try:
            r = await self._client.get(f"{BASE_URL}{path}", params=params)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                log.warning("finnhub rate-limited on %s, backing off 1s", path)
                await asyncio.sleep(1.0)
            else:
                log.warning("finnhub GET %s failed: %s", path, e)
            return {}
        except Exception as e:
            log.warning("finnhub GET %s failed: %s", path, e)
            return {}

    async def profile(self, symbol: str) -> dict:
        now = time.time()
        cached = self._profile_cache.get(symbol)
        if cached and now - cached[0] < 86400:  # 24h
            return cached[1]
        data = await self._get("/stock/profile2", symbol=symbol)
        if data:  # only cache successful responses
            self._profile_cache[symbol] = (now, data)
        return data

    async def quote(self, symbol: str) -> dict:
        """Returns {c: current, h: high, l: low, o: open, pc: prev close, t: ts}."""
        now = time.time()
        cached = self._quote_cache.get(symbol)
        if cached and now - cached[0] < 15:  # 15s
            return cached[1]
        data = await self._get("/quote", symbol=symbol)
        if data:  # only cache successful responses
            self._quote_cache[symbol] = (now, data)
        return data

    async def company_news(self, symbol: str, from_date: str, to_date: str) -> list[dict]:
        if not self.api_key:
            return []
        await self._throttle()
        try:
            r = await self._client.get(
                f"{BASE_URL}/company-news",
                params={"symbol": symbol, "from": from_date, "to": to_date, "token": self.api_key},
            )
            r.raise_for_status()
            return r.json() or []
        except Exception as e:
            log.warning("finnhub news failed: %s", e)
            return []
