"""Heatmap data builder.

Design goals (Render free tier friendly):

* **HTTP requests never block on Finnhub.** Fixed universes (`sp500`, `nasdaq`)
  are refreshed by a background task in `main.py`'s lifespan. Handlers call
  `get_cached(universe)` which is a dict lookup.
* **Stale-while-revalidate for watchlist.** Watchlist universes are
  user-specific so a background loop-per-user isn't viable. Instead
  `get_or_refresh_watchlist()` returns cached rows immediately (even if stale)
  and kicks off a background refresh if needed. Concurrent refreshes for the
  same key are deduplicated via a per-key lock.
* **Static profile data.** Name/sector/marketCap for fixed universes is baked
  into `heatmap_universe.py`, so refreshes only need live quote data and skip
  the Finnhub `/stock/profile2` endpoint entirely. Watchlist profiles still
  fall through to Finnhub (cached 24h on the client).
* **Disk persistence.** Snapshots of fixed universes are written to a JSON
  file so a container restart doesn't force a cold refetch.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .heatmap_universe import UNIVERSES, get_universe_symbols

if TYPE_CHECKING:
    from .finnhub_client import FinnhubClient

log = logging.getLogger(__name__)

# TTLs in seconds.
SP500_TTL = 300          # 5 min — matches background refresh cadence
NASDAQ_TTL = 600         # 10 min
WATCHLIST_TTL = 120      # 2 min — SWR threshold
WATCHLIST_STALE_MAX = 86_400  # 24h — anything older is treated as missing

# Snapshot on disk so a spin-down / restart doesn't blank the heatmap.
SNAPSHOT_PATH = Path(os.environ.get("HEATMAP_SNAPSHOT_PATH", "./heatmap_snapshot.json"))
SNAPSHOT_MAX_AGE = 86_400  # 24h — ignore snapshots older than this on load


class CacheEntry:
    __slots__ = ("rows", "updated_at")

    def __init__(self, rows: list[dict], updated_at: float) -> None:
        self.rows = rows
        self.updated_at = updated_at


class HeatmapService:
    def __init__(self, finnhub: "FinnhubClient") -> None:
        self.finnhub = finnhub
        self._cache: dict[str, CacheEntry] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _lock_for(self, key: str) -> asyncio.Lock:
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock

    def _ttl_for(self, universe: str) -> int:
        if universe == "sp500":
            return SP500_TTL
        if universe == "nasdaq":
            return NASDAQ_TTL
        return WATCHLIST_TTL

    def get_cached(self, key: str) -> CacheEntry | None:
        """Return the cached entry without triggering a fetch."""
        return self._cache.get(key)

    # ------------------------------------------------------------------
    # Row building
    # ------------------------------------------------------------------

    async def _quote_row(self, symbol: str, profile: dict[str, Any]) -> dict | None:
        """Fetch a live quote and combine it with a (static or Finnhub) profile."""
        quote = await self.finnhub.quote(symbol)
        c = quote.get("c")
        pc = quote.get("pc")
        if not c or not pc:
            return None
        c = float(c)
        pc = float(pc)
        change_pct = (c - pc) / pc * 100.0 if pc else 0.0
        return {
            "symbol": symbol,
            "name": profile.get("name") or symbol,
            "sector": profile.get("sector") or profile.get("finnhubIndustry") or "",
            "marketCap": float(profile.get("marketCap") or profile.get("marketCapitalization") or 0),
            "price": c,
            "prevClose": pc,
            "changePct": change_pct,
        }

    async def _row_fixed(self, universe: str, symbol: str) -> dict | None:
        entry = UNIVERSES[universe].get(symbol)
        if entry is None:
            return None
        # Cast TypedDict to plain dict for the helper signature.
        return await self._quote_row(symbol, dict(entry))

    async def _row_watchlist(self, symbol: str) -> dict | None:
        profile = await self.finnhub.profile(symbol)
        return await self._quote_row(symbol, profile or {})

    # ------------------------------------------------------------------
    # Refresh (does the actual work)
    # ------------------------------------------------------------------

    async def refresh_fixed(self, universe: str) -> list[dict]:
        """Refresh a fixed universe (`sp500` / `nasdaq`). Writes to cache + disk."""
        if universe not in UNIVERSES:
            return []
        symbols = get_universe_symbols(universe)
        lock = self._lock_for(universe)
        async with lock:
            t0 = time.time()
            results = await asyncio.gather(
                *(self._row_fixed(universe, s) for s in symbols),
                return_exceptions=True,
            )
            rows: list[dict] = []
            for r in results:
                if isinstance(r, Exception):
                    log.warning("heatmap row failed: %s", r)
                    continue
                if r and r.get("marketCap", 0) > 0:
                    rows.append(r)
            self._cache[universe] = CacheEntry(rows, time.time())
            log.info(
                "heatmap refresh %s: %d rows in %.1fs",
                universe,
                len(rows),
                time.time() - t0,
            )
            self._save_snapshot()
            return rows

    async def refresh_watchlist(self, symbols: list[str]) -> list[dict]:
        cache_key = self._watchlist_key(symbols)
        lock = self._lock_for(cache_key)
        async with lock:
            t0 = time.time()
            results = await asyncio.gather(
                *(self._row_watchlist(s) for s in symbols),
                return_exceptions=True,
            )
            rows: list[dict] = []
            for r in results:
                if isinstance(r, Exception):
                    log.warning("heatmap watchlist row failed: %s", r)
                    continue
                if r and r.get("marketCap", 0) > 0:
                    rows.append(r)
            self._cache[cache_key] = CacheEntry(rows, time.time())
            log.info(
                "heatmap refresh watchlist %s: %d rows in %.1fs",
                cache_key,
                len(rows),
                time.time() - t0,
            )
            return rows

    # ------------------------------------------------------------------
    # Public entry points used by the router
    # ------------------------------------------------------------------

    def get_fixed(self, universe: str) -> tuple[list[dict], float | None, bool, bool]:
        """Return `(rows, last_updated, stale, building)` for a fixed universe.

        Never fetches. The background loop owns refreshing.
        """
        entry = self._cache.get(universe)
        if entry is None:
            return [], None, False, True
        ttl = self._ttl_for(universe)
        stale = (time.time() - entry.updated_at) > ttl
        return entry.rows, entry.updated_at, stale, False

    async def get_or_refresh_watchlist(
        self, symbols: list[str]
    ) -> tuple[list[dict], float | None, bool, bool]:
        """Stale-while-revalidate for watchlist universes.

        Behaviour:
        - Fresh cache (<TTL): return it, stale=False.
        - Stale cache (<24h): return it immediately, fire a background refresh,
          stale=True.
        - Missing / >24h: fire a background refresh, return empty with
          building=True.
        """
        symbols = sorted({s.upper() for s in symbols if s})
        if not symbols:
            return [], None, False, False
        cache_key = self._watchlist_key(symbols)
        entry = self._cache.get(cache_key)
        now = time.time()

        if entry is not None:
            age = now - entry.updated_at
            if age < WATCHLIST_TTL:
                return entry.rows, entry.updated_at, False, False
            if age < WATCHLIST_STALE_MAX:
                # Serve stale; kick off a refresh in the background.
                self._spawn_background_refresh(symbols)
                return entry.rows, entry.updated_at, True, False
            # Too stale; fall through to "building" state.

        self._spawn_background_refresh(symbols)
        return [], None, False, True

    def _spawn_background_refresh(self, symbols: list[str]) -> None:
        cache_key = self._watchlist_key(symbols)
        lock = self._locks.get(cache_key)
        if lock is not None and lock.locked():
            return  # already refreshing
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self._safe_refresh_watchlist(symbols))

    async def _safe_refresh_watchlist(self, symbols: list[str]) -> None:
        try:
            await self.refresh_watchlist(symbols)
        except Exception as e:
            log.warning("background watchlist refresh failed: %s", e)

    @staticmethod
    def _watchlist_key(symbols: list[str]) -> str:
        return "wl:" + ",".join(sorted({s.upper() for s in symbols}))

    # ------------------------------------------------------------------
    # Disk persistence (fixed universes only)
    # ------------------------------------------------------------------

    def _save_snapshot(self) -> None:
        payload: dict[str, Any] = {}
        for universe in UNIVERSES:
            entry = self._cache.get(universe)
            if entry is None:
                continue
            payload[universe] = {"rows": entry.rows, "updated_at": entry.updated_at}
        if not payload:
            return
        try:
            SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
            # Atomic write: tempfile in same dir, then os.replace.
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=str(SNAPSHOT_PATH.parent),
                prefix=".heatmap_snapshot_",
                suffix=".tmp",
                delete=False,
            ) as f:
                json.dump(payload, f)
                tmp_path = f.name
            os.replace(tmp_path, SNAPSHOT_PATH)
        except Exception as e:
            log.warning("failed to write heatmap snapshot: %s", e)

    def load_snapshot(self) -> None:
        if not SNAPSHOT_PATH.exists():
            return
        try:
            with SNAPSHOT_PATH.open("r") as f:
                payload = json.load(f)
        except Exception as e:
            log.warning("failed to read heatmap snapshot: %s", e)
            return
        now = time.time()
        loaded = 0
        for universe, body in payload.items():
            if universe not in UNIVERSES:
                continue
            updated_at = float(body.get("updated_at", 0))
            if now - updated_at > SNAPSHOT_MAX_AGE:
                continue
            rows = body.get("rows") or []
            if not isinstance(rows, list):
                continue
            self._cache[universe] = CacheEntry(rows, updated_at)
            loaded += 1
        if loaded:
            log.info("heatmap snapshot loaded (%d universes)", loaded)
