from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/{symbol}")
async def get_profile(symbol: str, request: Request) -> dict:
    return await request.app.state.finnhub.profile(symbol.upper())
