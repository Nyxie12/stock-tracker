import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import get_db
from app.models.base import Base
from app.models import alert, paper, user, watchlist  # noqa: F401
from app.routers.auth import router as auth_router
from app.routers.watchlist import router as watchlist_router


@pytest.fixture
async def client():
    """Bare FastAPI app with auth + watchlist routers wired to an in-memory DB.

    No lifespan, so FinnhubStream/ConnectionManager never start.
    The watchlist router needs `request.app.state.finnhub` and `.stream`, so we
    stub those out with minimal fakes to keep the auth tests self-contained.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with Session() as s:
            yield s

    class _FakeFinnhub:
        async def profile(self, symbol):
            return {"name": f"{symbol} Inc."}

        async def quote(self, symbol):
            return {"c": 100.0, "pc": 99.0}

    class _FakeStream:
        def last_price(self, _symbol):
            return None

    app = FastAPI()
    app.include_router(auth_router)
    app.include_router(watchlist_router)
    app.dependency_overrides[get_db] = override_get_db
    app.state.finnhub = _FakeFinnhub()
    app.state.stream = _FakeStream()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await engine.dispose()


@pytest.mark.asyncio
async def test_register_returns_token_and_user(client):
    r = await client.post("/api/auth/register", json={"email": "a@example.com", "password": "secret1"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "a@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_rejected(client):
    await client.post("/api/auth/register", json={"email": "a@example.com", "password": "secret1"})
    r = await client.post("/api/auth/register", json={"email": "a@example.com", "password": "secret1"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_login_roundtrip(client):
    await client.post("/api/auth/register", json={"email": "a@example.com", "password": "secret1"})
    r = await client.post("/api/auth/login", json={"email": "a@example.com", "password": "secret1"})
    assert r.status_code == 200
    assert r.json()["access_token"]

    bad = await client.post("/api/auth/login", json={"email": "a@example.com", "password": "wrong"})
    assert bad.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_token(client):
    r = await client.get("/api/auth/me")
    assert r.status_code == 401

    reg = await client.post("/api/auth/register", json={"email": "a@example.com", "password": "secret1"})
    token = reg.json()["access_token"]
    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@example.com"


@pytest.mark.asyncio
async def test_watchlist_requires_auth_and_is_user_scoped(client):
    # Unauthenticated → 401
    r = await client.get("/api/watchlist")
    assert r.status_code == 401

    # Register two users
    t1 = (await client.post("/api/auth/register", json={"email": "a@example.com", "password": "secret1"})).json()["access_token"]
    t2 = (await client.post("/api/auth/register", json={"email": "b@example.com", "password": "secret1"})).json()["access_token"]
    h1 = {"Authorization": f"Bearer {t1}"}
    h2 = {"Authorization": f"Bearer {t2}"}

    # User 1 adds AAPL; user 2's list stays empty.
    r = await client.post("/api/watchlist", json={"symbol": "AAPL"}, headers=h1)
    assert r.status_code == 201

    r1 = await client.get("/api/watchlist", headers=h1)
    r2 = await client.get("/api/watchlist", headers=h2)
    assert r1.status_code == 200 and r2.status_code == 200
    assert [i["symbol"] for i in r1.json()] == ["AAPL"]
    assert r2.json() == []
