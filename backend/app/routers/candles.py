from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query

from ..services.yfinance_service import TIMEFRAMES, get_candles

router = APIRouter(prefix="/api/candles", tags=["candles"])


@router.get("/{symbol}")
async def candles(
    symbol: str,
    timeframe: str = Query("1D", description="1D|1W|1M|1Y"),
) -> dict:
    tf = timeframe.upper()
    if tf not in TIMEFRAMES:
        raise HTTPException(400, f"timeframe must be one of {list(TIMEFRAMES)}")
    data, stale = await get_candles(symbol, tf)
    return {
        "symbol": symbol.upper(),
        "timeframe": tf,
        "stale": stale,
        "candles": [asdict(c) for c in data],
    }
