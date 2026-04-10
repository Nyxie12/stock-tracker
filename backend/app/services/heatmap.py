"""Heatmap data builder.

For each symbol in the chosen universe, fetch (name, marketCap, sector) from
Finnhub profile (cached 24h) and (current, prevClose) from Finnhub quote
(cached 15s), then compute changePct. Results are cached per universe for 60s
to stay well within Finnhub free-tier REST limits.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .finnhub_client import FinnhubClient

# A compact, recognizable universe. The plan references ~500 symbols, but
# Finnhub's free tier (~60 req/min) makes a 500-symbol refresh unrealistic.
# This curated list keeps the heatmap useful while respecting rate limits.
SP500_TOP: list[str] = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B",
    "AVGO", "LLY", "JPM", "V", "WMT", "XOM", "UNH", "MA", "PG", "JNJ",
    "HD", "COST",
]


class HeatmapService:
    def __init__(self, finnhub: "FinnhubClient") -> None:
        self.finnhub = finnhub
        self._cache: dict[str, tuple[float, list[dict]]] = {}

    async def _row_for(self, symbol: str) -> dict | None:
        profile = await self.finnhub.profile(symbol)
        quote = await self.finnhub.quote(symbol)
        if not quote.get("c") or not quote.get("pc"):
            return None
        c = float(quote["c"])
        pc = float(quote["pc"])
        change_pct = (c - pc) / pc * 100.0 if pc else 0.0
        market_cap = float(profile.get("marketCapitalization", 0) or 0)
        return {
            "symbol": symbol,
            "name": profile.get("name") or symbol,
            "sector": profile.get("finnhubIndustry") or "",
            "marketCap": market_cap,
            "price": c,
            "prevClose": pc,
            "changePct": change_pct,
        }

    async def build(self, universe: str, watchlist_symbols: list[str] | None = None) -> list[dict]:
        cache_key = universe
        if universe == "watchlist":
            symbols = [s.upper() for s in (watchlist_symbols or [])]
            cache_key = "wl:" + ",".join(sorted(symbols))
        else:
            symbols = SP500_TOP

        now = time.time()
        cached = self._cache.get(cache_key)
        if cached and now - cached[0] < 60:
            return cached[1]

        # Fetch sequentially to avoid hammering Finnhub free tier all at once;
        # small bounded concurrency keeps wall-time reasonable.
        sem = asyncio.Semaphore(2)

        async def guarded(sym: str) -> dict | None:
            async with sem:
                return await self._row_for(sym)

        results = await asyncio.gather(*(guarded(s) for s in symbols))
        rows = [r for r in results if r and r["marketCap"] > 0]
        self._cache[cache_key] = (now, rows)
        return rows
