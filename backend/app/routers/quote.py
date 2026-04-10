from fastapi import APIRouter, Request

from ..schemas.quote import QuoteOut

router = APIRouter(prefix="/api/quote", tags=["quote"])


@router.get("/{symbol}")
async def get_quote(symbol: str, request: Request) -> dict:
    quote = await request.app.state.finnhub.quote(symbol.upper())
    return quote
