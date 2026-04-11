from datetime import datetime
from zoneinfo import ZoneInfo

from app.utils.market_hours import (
    AFTERHOURS_CLOSE,
    PREMARKET_OPEN,
    REGULAR_OPEN,
    current_session,
    is_market_open,
    market_status,
)

ET = ZoneInfo("America/New_York")


def at(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=ET)


# 2026-04-13 is a Monday, 2026-04-18 is a Saturday.


def test_weekend_is_closed():
    sat = at(2026, 4, 18, 12, 0)
    sun = at(2026, 4, 19, 12, 0)
    assert not is_market_open(sat)
    assert not is_market_open(sun)
    assert current_session(sat) == "closed"
    assert current_session(sun) == "closed"


def test_premarket_window_open():
    assert is_market_open(at(2026, 4, 13, 4, 0))
    assert is_market_open(at(2026, 4, 13, 9, 29))
    assert current_session(at(2026, 4, 13, 5, 30)) == "pre"


def test_regular_session_open():
    assert is_market_open(at(2026, 4, 13, 9, 30))
    assert is_market_open(at(2026, 4, 13, 15, 59))
    assert current_session(at(2026, 4, 13, 12, 0)) == "regular"


def test_afterhours_open():
    assert is_market_open(at(2026, 4, 13, 16, 0))
    assert is_market_open(at(2026, 4, 13, 19, 59))
    assert current_session(at(2026, 4, 13, 18, 0)) == "post"


def test_overnight_closed():
    assert not is_market_open(at(2026, 4, 13, 20, 0))  # exactly close
    assert not is_market_open(at(2026, 4, 13, 23, 0))
    assert not is_market_open(at(2026, 4, 14, 3, 59))
    assert current_session(at(2026, 4, 13, 21, 0)) == "closed"
    assert current_session(at(2026, 4, 14, 1, 0)) == "closed"


def test_market_status_payload():
    s = market_status(at(2026, 4, 13, 12, 0))
    assert s["open"] is True
    assert s["session"] == "regular"
    assert "next_open_iso" in s
    assert "now_iso" in s


def test_next_open_skips_weekend():
    s = market_status(at(2026, 4, 17, 22, 0))  # Friday after-close
    assert s["open"] is False
    # Next open should be Monday 4:00 ET, not Saturday.
    nxt = datetime.fromisoformat(s["next_open_iso"])
    assert nxt.weekday() == 0  # Monday
    assert nxt.hour == PREMARKET_OPEN.hour
    assert nxt.minute == PREMARKET_OPEN.minute


def test_constants_sane():
    assert PREMARKET_OPEN < REGULAR_OPEN < AFTERHOURS_CLOSE
