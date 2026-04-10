from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models.watchlist import WatchlistItem

router = APIRouter(prefix="/api/heatmap", tags=["heatmap"])


@router.get("")
async def heatmap(
    request: Request,
    universe: str = Query("sp500", pattern="^(sp500|watchlist)$"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    watchlist_symbols: list[str] = []
    if universe == "watchlist":
        res = await db.execute(select(WatchlistItem.symbol))
        watchlist_symbols = [r for r, in res.all()]
    rows = await request.app.state.heatmap.build(universe, watchlist_symbols)
    return {"universe": universe, "rows": rows}
