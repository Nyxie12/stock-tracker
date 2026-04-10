from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..config import settings

router = APIRouter(prefix="/api/debug", tags=["debug"])


class TickIn(BaseModel):
    symbol: str
    price: float


@router.post("/tick")
async def inject_tick(payload: TickIn, request: Request) -> dict:
    if not settings.debug:
        raise HTTPException(404, "Not found")
    await request.app.state.stream.inject(payload.symbol, payload.price)
    return {"ok": True}
