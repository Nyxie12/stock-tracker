import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models import alert, paper, watchlist  # noqa: F401
from app.services import paper_trading


class FakeStream:
    def __init__(self) -> None:
        self._px: dict[str, float] = {}

    def set(self, symbol: str, price: float) -> None:
        self._px[symbol.upper()] = price

    def last_price(self, symbol: str) -> float | None:
        return self._px.get(symbol.upper())


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as db:
        yield db
    await engine.dispose()


@pytest.mark.asyncio
async def test_buy_updates_cash_and_position(session):
    stream = FakeStream()
    stream.set("AAPL", 150)
    trade = await paper_trading.buy(session, stream, "AAPL", 10)
    assert trade.side == "buy"
    view = await paper_trading.portfolio_view(session, stream)
    assert view["cash"] == pytest.approx(100000 - 10 * 150)
    assert len(view["positions"]) == 1
    pos = view["positions"][0]
    assert pos["symbol"] == "AAPL"
    assert pos["quantity"] == 10
    assert pos["avg_cost"] == pytest.approx(150)


@pytest.mark.asyncio
async def test_buy_twice_weighted_avg(session):
    stream = FakeStream()
    stream.set("AAPL", 150)
    await paper_trading.buy(session, stream, "AAPL", 10)
    stream.set("AAPL", 170)
    await paper_trading.buy(session, stream, "AAPL", 10)
    view = await paper_trading.portfolio_view(session, stream)
    pos = view["positions"][0]
    assert pos["quantity"] == 20
    assert pos["avg_cost"] == pytest.approx(160)
    assert view["cash"] == pytest.approx(100000 - 10 * 150 - 10 * 170)


@pytest.mark.asyncio
async def test_sell_partial_preserves_avg_cost(session):
    stream = FakeStream()
    stream.set("AAPL", 150)
    await paper_trading.buy(session, stream, "AAPL", 20)
    # avg = 150
    stream.set("AAPL", 180)
    await paper_trading.sell(session, stream, "AAPL", 5)
    view = await paper_trading.portfolio_view(session, stream)
    pos = view["positions"][0]
    assert pos["quantity"] == 15
    assert pos["avg_cost"] == pytest.approx(150)  # unchanged on sell
    assert view["cash"] == pytest.approx(100000 - 20 * 150 + 5 * 180)


@pytest.mark.asyncio
async def test_sell_to_zero_removes_position(session):
    stream = FakeStream()
    stream.set("AAPL", 150)
    await paper_trading.buy(session, stream, "AAPL", 5)
    stream.set("AAPL", 160)
    await paper_trading.sell(session, stream, "AAPL", 5)
    view = await paper_trading.portfolio_view(session, stream)
    assert len(view["positions"]) == 0
    assert view["cash"] == pytest.approx(100000 - 5 * 150 + 5 * 160)


@pytest.mark.asyncio
async def test_sell_more_than_held_rejects(session):
    stream = FakeStream()
    stream.set("AAPL", 150)
    await paper_trading.buy(session, stream, "AAPL", 5)
    with pytest.raises(ValueError, match="insufficient position"):
        await paper_trading.sell(session, stream, "AAPL", 10)


@pytest.mark.asyncio
async def test_buy_exceeding_cash_rejects(session):
    stream = FakeStream()
    stream.set("AAPL", 1_000_000)
    with pytest.raises(ValueError, match="insufficient cash"):
        await paper_trading.buy(session, stream, "AAPL", 1)


@pytest.mark.asyncio
async def test_buy_without_live_price_rejects(session):
    stream = FakeStream()
    with pytest.raises(ValueError, match="no live price"):
        await paper_trading.buy(session, stream, "AAPL", 1)
