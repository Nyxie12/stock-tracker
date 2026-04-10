from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import get_current_user_optional
from ..models.user import User
from ..models.watchlist import Watchlist, WatchlistItem

router = APIRouter(prefix="/api/heatmap", tags=["heatmap"])


@router.get("")
async def heatmap(
    request: Request,
    universe: str = Query("sp500", pattern="^(sp500|watchlist)$"),
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> dict:
    watchlist_symbols: list[str] = []
    if universe == "watchlist":
        if user is None:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Authentication required for watchlist heatmap",
            )
        res = await db.execute(
            select(WatchlistItem.symbol)
            .join(Watchlist, WatchlistItem.watchlist_id == Watchlist.id)
            .where(Watchlist.user_id == user.id)
        )
        watchlist_symbols = [r for r, in res.all()]
    rows = await request.app.state.heatmap.build(universe, watchlist_symbols)
    return {"universe": universe, "rows": rows}
