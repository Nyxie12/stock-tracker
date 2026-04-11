from collections.abc import AsyncIterator

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings

engine = create_async_engine(settings.database_url, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_connection, _):  # type: ignore[no-untyped-def]
    # Only applies to SQLite. Enables WAL and sane foreign keys.
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        pass


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def init_models() -> None:
    from sqlalchemy import text

    from .models.base import Base  # noqa: F401
    # Import all models so they register on Base.metadata
    from .models import alert, paper, user, watchlist  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # One-shot ALTER for columns added after the original create_all run.
        # SQLite-only; idempotent (catches "duplicate column" errors).
        for stmt in (
            "ALTER TABLE paper_portfolios ADD COLUMN realized_pnl NUMERIC(18, 4) NOT NULL DEFAULT 0",
            "ALTER TABLE paper_trades ADD COLUMN realized_pnl NUMERIC(18, 4)",
        ):
            try:
                await conn.execute(text(stmt))
            except Exception:
                pass
