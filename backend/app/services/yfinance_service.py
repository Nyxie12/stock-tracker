"""yfinance wrapper.

yfinance is synchronous and scrapes Yahoo. We:
  - Run it inside a threadpool so it doesn't block the event loop.
  - Cache responses per (symbol, timeframe) with TTL to reduce rate-limit risk.
  - On failure, fall back to the last cached value with `stale: true`.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from fastapi.concurrency import run_in_threadpool

import yfinance as yf

log = logging.getLogger(__name__)

# timeframe -> (yfinance period, interval, cache ttl seconds)
TIMEFRAMES: dict[str, tuple[str, str, int]] = {
    "1D": ("1d", "5m", 60),
    "1W": ("5d", "30m", 120),
    "1M": ("1mo", "1d", 900),
    "1Y": ("1y", "1d", 3600),
}


@dataclass
class Candle:
    time: int  # unix seconds
    open: float
    high: float
    low: float
    close: float
    volume: float


_cache: dict[tuple[str, str], tuple[float, list[Candle]]] = {}


def _fetch_sync(symbol: str, period: str, interval: str) -> list[Candle]:
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=period, interval=interval, auto_adjust=False)
    out: list[Candle] = []
    for ts, row in hist.iterrows():
        try:
            out.append(
                Candle(
                    time=int(ts.timestamp()),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row.get("Volume", 0) or 0),
                )
            )
        except Exception:
            continue
    return out


async def get_candles(symbol: str, timeframe: str) -> tuple[list[Candle], bool]:
    """Returns (candles, stale_flag)."""
    symbol = symbol.upper()
    tf = timeframe.upper()
    if tf not in TIMEFRAMES:
        raise ValueError(f"unknown timeframe: {timeframe}")
    period, interval, ttl = TIMEFRAMES[tf]
    key = (symbol, tf)
    now = time.time()
    cached = _cache.get(key)
    if cached and now - cached[0] < ttl:
        return cached[1], False
    try:
        data = await run_in_threadpool(_fetch_sync, symbol, period, interval)
        if data:
            _cache[key] = (now, data)
            return data, False
        if cached:
            return cached[1], True
        return [], False
    except Exception as e:
        log.warning("yfinance fetch failed for %s %s: %s", symbol, tf, e)
        if cached:
            return cached[1], True
        return [], True
