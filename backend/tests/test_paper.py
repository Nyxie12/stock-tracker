from datetime import datetime, timedelta

import pytest
from freezegun import freeze_time
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import alert, paper, user, watchlist  # noqa: F401
from app.models.base import Base
from app.models.paper import SettlementEvent
from app.models.user import User
from app.services import paper_trading

# All tests freeze time to a Monday at 12:00 ET (16:00 UTC) — regular session.
# 2026-04-13 is a Monday.
MARKET_OPEN_UTC = "2026-04-13 16:00:00"


class FakeStream:
    def __init__(self) -> None:
        self._px: dict[str, float] = {}

    def set(self, symbol: str, price: float) -> None:
        self._px[symbol.upper()] = price

    def last_price(self, symbol: str) -> float | None:
        return self._px.get(symbol.upper())


@pytest.fixture
async def session_and_portfolio():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        u = User(email="t@example.com", password_hash="x")
        db.add(u)
        await db.flush()
        p = await paper_trading.get_portfolio_for_user(db, u.id)
        yield db, p
    await engine.dispose()


# ─── Original buy/sell math (now wrapped in freeze_time) ────────────────────


@pytest.mark.asyncio
@freeze_time(MARKET_OPEN_UTC)
async def test_buy_updates_cash_and_position(session_and_portfolio):
    db, p = session_and_portfolio
    stream = FakeStream()
    stream.set("AAPL", 150)
    trade = await paper_trading.buy(db, stream, None, p, "AAPL", 10)
    assert trade.side == "buy"
    view = await paper_trading.portfolio_view(db, stream, None, p)
    assert view["cash"] == pytest.approx(100000 - 10 * 150)
    assert len(view["positions"]) == 1
    pos = view["positions"][0]
    assert pos["symbol"] == "AAPL"
    assert pos["quantity"] == 10
    assert pos["avg_cost"] == pytest.approx(150)


@pytest.mark.asyncio
@freeze_time(MARKET_OPEN_UTC)
async def test_buy_twice_weighted_avg(session_and_portfolio):
    db, p = session_and_portfolio
    stream = FakeStream()
    stream.set("AAPL", 150)
    await paper_trading.buy(db, stream, None, p, "AAPL", 10)
    stream.set("AAPL", 170)
    await paper_trading.buy(db, stream, None, p, "AAPL", 10)
    view = await paper_trading.portfolio_view(db, stream, None, p)
    pos = view["positions"][0]
    assert pos["quantity"] == 20
    assert pos["avg_cost"] == pytest.approx(160)
    assert view["cash"] == pytest.approx(100000 - 10 * 150 - 10 * 170)


@pytest.mark.asyncio
@freeze_time(MARKET_OPEN_UTC)
async def test_sell_partial_preserves_avg_cost(session_and_portfolio):
    db, p = session_and_portfolio
    stream = FakeStream()
    stream.set("AAPL", 150)
    await paper_trading.buy(db, stream, None, p, "AAPL", 20)
    stream.set("AAPL", 180)
    await paper_trading.sell(db, stream, None, p, "AAPL", 5)
    view = await paper_trading.portfolio_view(db, stream, None, p)
    pos = view["positions"][0]
    assert pos["quantity"] == 15
    assert pos["avg_cost"] == pytest.approx(150)  # unchanged on sell
    assert view["cash"] == pytest.approx(100000 - 20 * 150 + 5 * 180)


@pytest.mark.asyncio
@freeze_time(MARKET_OPEN_UTC)
async def test_sell_to_zero_removes_position(session_and_portfolio):
    db, p = session_and_portfolio
    stream = FakeStream()
    stream.set("AAPL", 150)
    await paper_trading.buy(db, stream, None, p, "AAPL", 5)
    stream.set("AAPL", 160)
    await paper_trading.sell(db, stream, None, p, "AAPL", 5)
    view = await paper_trading.portfolio_view(db, stream, None, p)
    assert len(view["positions"]) == 0
    assert view["cash"] == pytest.approx(100000 - 5 * 150 + 5 * 160)


@pytest.mark.asyncio
@freeze_time(MARKET_OPEN_UTC)
async def test_sell_more_than_held_rejects(session_and_portfolio):
    db, p = session_and_portfolio
    stream = FakeStream()
    stream.set("AAPL", 150)
    await paper_trading.buy(db, stream, None, p, "AAPL", 5)
    with pytest.raises(ValueError, match="insufficient position"):
        await paper_trading.sell(db, stream, None, p, "AAPL", 10)


@pytest.mark.asyncio
@freeze_time(MARKET_OPEN_UTC)
async def test_buy_exceeding_cash_rejects(session_and_portfolio):
    db, p = session_and_portfolio
    stream = FakeStream()
    stream.set("AAPL", 1_000_000)
    with pytest.raises(ValueError, match="insufficient"):
        await paper_trading.buy(db, stream, None, p, "AAPL", 1)


@pytest.mark.asyncio
@freeze_time(MARKET_OPEN_UTC)
async def test_buy_without_live_price_rejects(session_and_portfolio):
    db, p = session_and_portfolio
    stream = FakeStream()
    with pytest.raises(ValueError, match="no live price"):
        await paper_trading.buy(db, stream, None, p, "AAPL", 1)


@pytest.mark.asyncio
@freeze_time(MARKET_OPEN_UTC)
async def test_portfolios_are_isolated_per_user():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        u1 = User(email="a@example.com", password_hash="x")
        u2 = User(email="b@example.com", password_hash="x")
        db.add_all([u1, u2])
        await db.flush()

        p1 = await paper_trading.get_portfolio_for_user(db, u1.id)
        p2 = await paper_trading.get_portfolio_for_user(db, u2.id)

        stream = FakeStream()
        stream.set("AAPL", 100)
        await paper_trading.buy(db, stream, None, p1, "AAPL", 5)

        v1 = await paper_trading.portfolio_view(db, stream, None, p1)
        v2 = await paper_trading.portfolio_view(db, stream, None, p2)
        assert len(v1["positions"]) == 1
        assert len(v2["positions"]) == 0
        assert v2["cash"] == pytest.approx(100000)
    await engine.dispose()


# ─── Market hours enforcement ───────────────────────────────────────────────


@pytest.mark.asyncio
@freeze_time("2026-04-18 16:00:00")  # Saturday — closed
async def test_buy_blocked_when_market_closed(session_and_portfolio):
    db, p = session_and_portfolio
    stream = FakeStream()
    stream.set("AAPL", 150)
    with pytest.raises(ValueError, match="Market is closed"):
        await paper_trading.buy(db, stream, None, p, "AAPL", 1)


@pytest.mark.asyncio
@freeze_time("2026-04-18 16:00:00")  # Saturday — closed
async def test_sell_blocked_when_market_closed(session_and_portfolio):
    db, p = session_and_portfolio
    stream = FakeStream()
    stream.set("AAPL", 150)
    # Set up a position by hand (skip market check)
    await paper_trading.buy(
        db, stream, None, p, "AAPL", 1, skip_market_check=True
    )
    with pytest.raises(ValueError, match="Market is closed"):
        await paper_trading.sell(db, stream, None, p, "AAPL", 1)


# ─── Settlement grace period ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sell_proceeds_unsettled_for_one_hour(session_and_portfolio):
    db, p = session_and_portfolio
    stream = FakeStream()
    stream.set("AAPL", 100)

    with freeze_time(MARKET_OPEN_UTC) as frozen:
        # Buy 100 shares of AAPL @ $100 → spend all 10k slot of cash
        await paper_trading.buy(db, stream, None, p, "AAPL", 100)
        # Cash now: 100000 - 10000 = 90000
        await paper_trading.sell(db, stream, None, p, "AAPL", 100)
        # Cash now: 90000 + 10000 = 100000, but 10000 is unsettled.

        bp, pending, _ = await paper_trading.compute_buying_power(db, p)
        assert pending == pytest.approx(10000)
        assert bp == pytest.approx(90000)

        # Try to buy 100 more shares — should fail (need 10k buying power)
        # 90k buying power can only buy 900 shares, so try 1000 to exceed
        stream.set("MSFT", 100)
        with pytest.raises(ValueError, match="insufficient|still settling"):
            await paper_trading.buy(db, stream, None, p, "MSFT", 1000)

        # Buying within available buying power still works.
        await paper_trading.buy(db, stream, None, p, "MSFT", 100)

        # Advance 59 minutes — still pending
        frozen.tick(delta=timedelta(minutes=59))
        bp, pending, _ = await paper_trading.compute_buying_power(db, p)
        assert pending == pytest.approx(10000)

        # Advance past 1h total
        frozen.tick(delta=timedelta(minutes=2))
        bp, pending, _ = await paper_trading.compute_buying_power(db, p)
        assert pending == pytest.approx(0)


# ─── Realized P&L ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@freeze_time(MARKET_OPEN_UTC)
async def test_realized_pnl_accumulates(session_and_portfolio):
    db, p = session_and_portfolio
    stream = FakeStream()
    stream.set("AAPL", 100)
    await paper_trading.buy(db, stream, None, p, "AAPL", 10)  # cost 1000

    stream.set("AAPL", 120)
    trade1 = await paper_trading.sell(db, stream, None, p, "AAPL", 5)
    # realized: (120 - 100) * 5 = 100
    assert trade1.realized_pnl == pytest.approx(100)

    stream.set("AAPL", 90)
    trade2 = await paper_trading.sell(db, stream, None, p, "AAPL", 5)
    # realized: (90 - 100) * 5 = -50
    assert trade2.realized_pnl == pytest.approx(-50)

    # Refresh portfolio to pick up updated realized_pnl
    await db.refresh(p)
    assert float(p.realized_pnl) == pytest.approx(50)

    view = await paper_trading.portfolio_view(db, stream, None, p)
    assert view["realized_pnl"] == pytest.approx(50)


# ─── Reset portfolio ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
@freeze_time(MARKET_OPEN_UTC)
async def test_reset_portfolio(session_and_portfolio):
    db, p = session_and_portfolio
    stream = FakeStream()
    stream.set("AAPL", 100)
    await paper_trading.buy(db, stream, None, p, "AAPL", 10)
    stream.set("AAPL", 120)
    await paper_trading.sell(db, stream, None, p, "AAPL", 5)

    await paper_trading.reset_portfolio(db, p)

    view = await paper_trading.portfolio_view(db, stream, None, p)
    assert view["cash"] == pytest.approx(100000)
    assert view["realized_pnl"] == pytest.approx(0)
    assert len(view["positions"]) == 0
    assert view["pending_settlement"] == pytest.approx(0)

    # No leftover settlement rows.
    from sqlalchemy import select
    res = await db.execute(select(SettlementEvent).where(SettlementEvent.portfolio_id == p.id))
    assert res.scalars().all() == []
