from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models.watchlist import Watchlist, WatchlistItem
from ..schemas.watchlist import WatchlistItemCreate, WatchlistItemOut

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


async def _get_default_watchlist(db: AsyncSession) -> Watchlist:
    res = await db.execute(select(Watchlist).order_by(Watchlist.id).limit(1))
    wl = res.scalar_one_or_none()
    if wl is None:
        wl = Watchlist(name="Default")
        db.add(wl)
        await db.commit()
        await db.refresh(wl)
    return wl


@router.get("", response_model=list[WatchlistItemOut])
async def list_items(request: Request, db: AsyncSession = Depends(get_db)) -> list[WatchlistItemOut]:
    wl = await _get_default_watchlist(db)
    res = await db.execute(
        select(WatchlistItem).where(WatchlistItem.watchlist_id == wl.id).order_by(WatchlistItem.added_at)
    )
    items = res.scalars().all()

    finnhub = request.app.state.finnhub
    stream = request.app.state.stream

    out: list[WatchlistItemOut] = []
    for item in items:
        profile = await finnhub.profile(item.symbol)
        quote = await finnhub.quote(item.symbol)
        last = stream.last_price(item.symbol)
        if last is None and quote.get("c"):
            last = float(quote["c"])
        prev_close = float(quote["pc"]) if quote.get("pc") else None
        change_pct = None
        if last is not None and prev_close:
            change_pct = (last - prev_close) / prev_close * 100.0
        out.append(
            WatchlistItemOut(
                symbol=item.symbol,
                added_at=item.added_at,
                name=profile.get("name") if profile else None,
                last_price=last,
                prev_close=prev_close,
                change_pct=change_pct,
            )
        )
    return out


@router.post("", response_model=WatchlistItemOut, status_code=201)
async def add_item(
    payload: WatchlistItemCreate, request: Request, db: AsyncSession = Depends(get_db)
) -> WatchlistItemOut:
    symbol = payload.symbol.upper().strip()
    if not symbol:
        raise HTTPException(400, "Symbol required")

    finnhub = request.app.state.finnhub

    # Validate that the ticker actually exists
    profile = await finnhub.profile(symbol)
    if not profile or not profile.get("name"):
        raise HTTPException(404, f"Ticker '{symbol}' not found. Check the symbol and try again.")

    wl = await _get_default_watchlist(db)
    existing = await db.execute(
        select(WatchlistItem).where(WatchlistItem.watchlist_id == wl.id, WatchlistItem.symbol == symbol)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"{symbol} already in watchlist")
    item = WatchlistItem(watchlist_id=wl.id, symbol=symbol)
    db.add(item)
    await db.commit()
    await db.refresh(item)

    quote = await finnhub.quote(symbol)
    last = float(quote["c"]) if quote.get("c") else None
    prev_close = float(quote["pc"]) if quote.get("pc") else None
    change_pct = None
    if last is not None and prev_close:
        change_pct = (last - prev_close) / prev_close * 100.0

    return WatchlistItemOut(
        symbol=item.symbol,
        added_at=item.added_at,
        name=profile.get("name") if profile else None,
        last_price=last,
        prev_close=prev_close,
        change_pct=change_pct,
    )


@router.delete("/{symbol}", status_code=204)
async def remove_item(symbol: str, db: AsyncSession = Depends(get_db)) -> None:
    symbol = symbol.upper().strip()
    wl = await _get_default_watchlist(db)
    res = await db.execute(
        select(WatchlistItem).where(WatchlistItem.watchlist_id == wl.id, WatchlistItem.symbol == symbol)
    )
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Not found")
    await db.delete(item)
    await db.commit()
