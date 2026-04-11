from decimal import Decimal

import pytest
from freezegun import freeze_time
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import alert, paper, user, watchlist  # noqa: F401
from app.models.base import Base
from app.models.paper import LimitOrder
from app.models.user import User
from app.services import paper_trading

# Monday 12:00 ET = 16:00 UTC, regular session.
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


@pytest.mark.asyncio
@freeze_time(MARKET_OPEN_UTC)
async def test_place_buy_limit_reserves_buying_power(session_and_portfolio):
    db, p = session_and_portfolio
    order = await paper_trading.place_limit_order(
        db, p, "AAPL", "buy", 10, Decimal("100")
    )
    assert order.status == "open"
    bp, _, reserved = await paper_trading.compute_buying_power(db, p)
    assert reserved == pytest.approx(1000)
    assert bp == pytest.approx(99000)


@pytest.mark.asyncio
@freeze_time(MARKET_OPEN_UTC)
async def test_buy_limit_rejects_when_insufficient_buying_power(session_and_portfolio):
    db, p = session_and_portfolio
    with pytest.raises(ValueError, match="insufficient buying power"):
        await paper_trading.place_limit_order(db, p, "AAPL", "buy", 100_000, Decimal("100"))


@pytest.mark.asyncio
@freeze_time(MARKET_OPEN_UTC)
async def test_sell_limit_reserves_position(session_and_portfolio):
    db, p = session_and_portfolio
    stream = FakeStream()
    stream.set("AAPL", 100)
    await paper_trading.buy(db, stream, None, p, "AAPL", 10)

    await paper_trading.place_limit_order(db, p, "AAPL", "sell", 6, Decimal("120"))

    # Trying to sell 5 more should fail because 6 are reserved.
    with pytest.raises(ValueError, match="insufficient position"):
        await paper_trading.sell(db, stream, None, p, "AAPL", 5)

    # Selling 4 (= 10 - 6) is fine.
    await paper_trading.sell(db, stream, None, p, "AAPL", 4)


@pytest.mark.asyncio
@freeze_time(MARKET_OPEN_UTC)
async def test_cancel_releases_reservation(session_and_portfolio):
    db, p = session_and_portfolio
    order = await paper_trading.place_limit_order(
        db, p, "AAPL", "buy", 10, Decimal("100")
    )
    bp_before, _, _ = await paper_trading.compute_buying_power(db, p)
    assert bp_before == pytest.approx(99000)

    await paper_trading.cancel_limit_order(db, p, order.id)

    bp_after, _, _ = await paper_trading.compute_buying_power(db, p)
    assert bp_after == pytest.approx(100000)
    refreshed = await db.get(LimitOrder, order.id)
    assert refreshed.status == "cancelled"


@pytest.mark.asyncio
@freeze_time(MARKET_OPEN_UTC)
async def test_list_limit_orders_filters_by_status(session_and_portfolio):
    db, p = session_and_portfolio
    o1 = await paper_trading.place_limit_order(db, p, "AAPL", "buy", 1, Decimal("100"))
    await paper_trading.place_limit_order(db, p, "MSFT", "buy", 1, Decimal("200"))
    await paper_trading.cancel_limit_order(db, p, o1.id)

    open_orders = await paper_trading.list_limit_orders(db, p, status="open")
    assert len(open_orders) == 1
    assert open_orders[0].symbol == "MSFT"


@pytest.mark.asyncio
@freeze_time(MARKET_OPEN_UTC)
async def test_buy_limit_skips_buying_power_check_on_fill(session_and_portfolio):
    """Once the engine fills a buy limit order, the buy itself shouldn't double-
    deduct buying power. We use skip_buying_power_check=True for that path."""
    db, p = session_and_portfolio
    stream = FakeStream()
    stream.set("AAPL", 95)

    # Place a buy limit at $100 reserving $1000 of buying power.
    order = await paper_trading.place_limit_order(
        db, p, "AAPL", "buy", 10, Decimal("100")
    )
    assert order.status == "open"

    # Mark it filled before the buy executes (matches engine flow).
    order.status = "filled"
    await db.commit()

    # Now buying 10 shares at $95 should succeed even if we'd be tight on cash.
    await paper_trading.buy(
        db, stream, None, p, "AAPL", 10, skip_buying_power_check=True
    )

    pos = next(
        x for x in (await paper_trading.portfolio_view(db, stream, None, p))["positions"]
        if x["symbol"] == "AAPL"
    )
    assert pos["quantity"] == 10
