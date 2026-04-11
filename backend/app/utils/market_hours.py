"""
US equity market hours.

Trades are allowed during extended hours (4:00–20:00 ET) on weekdays.
No holiday calendar — documented trade-off; rejects on weekends only.

`is_market_open()` is the gate used by paper_trading.buy/sell. `market_status()`
powers the frontend status pill and tells callers when the next session starts.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

PREMARKET_OPEN = time(4, 0)
REGULAR_OPEN = time(9, 30)
REGULAR_CLOSE = time(16, 0)
AFTERHOURS_CLOSE = time(20, 0)


def _now_et(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(tz=ET)
    if now.tzinfo is None:
        return now.replace(tzinfo=ET)
    return now.astimezone(ET)


def is_market_open(now: datetime | None = None) -> bool:
    """True during 4:00–20:00 ET on weekdays. No holiday calendar."""
    n = _now_et(now)
    if n.weekday() >= 5:  # Sat=5, Sun=6
        return False
    t = n.time()
    return PREMARKET_OPEN <= t < AFTERHOURS_CLOSE


def current_session(now: datetime | None = None) -> str:
    """Returns 'pre' | 'regular' | 'post' | 'closed'."""
    n = _now_et(now)
    if n.weekday() >= 5:
        return "closed"
    t = n.time()
    if PREMARKET_OPEN <= t < REGULAR_OPEN:
        return "pre"
    if REGULAR_OPEN <= t < REGULAR_CLOSE:
        return "regular"
    if REGULAR_CLOSE <= t < AFTERHOURS_CLOSE:
        return "post"
    return "closed"


def next_open(now: datetime | None = None) -> datetime:
    """Datetime (ET) of the next premarket open. If currently open, returns now."""
    n = _now_et(now)
    if is_market_open(n):
        return n
    candidate = n.replace(hour=PREMARKET_OPEN.hour, minute=PREMARKET_OPEN.minute, second=0, microsecond=0)
    # If today's premarket already passed (or it's a weekend), advance day-by-day.
    if n.time() >= PREMARKET_OPEN or n.weekday() >= 5:
        candidate = candidate + timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate = candidate + timedelta(days=1)
    return candidate


def market_status(now: datetime | None = None) -> dict:
    n = _now_et(now)
    is_open = is_market_open(n)
    session = current_session(n)
    nxt = next_open(n) if not is_open else n
    return {
        "open": is_open,
        "session": session,
        "next_open_iso": nxt.isoformat(),
        "now_iso": n.isoformat(),
    }
