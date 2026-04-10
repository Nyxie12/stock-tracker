from datetime import datetime

from pydantic import BaseModel, Field


class WatchlistItemCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)


class WatchlistItemOut(BaseModel):
    symbol: str
    added_at: datetime
    name: str | None = None
    last_price: float | None = None
    prev_close: float | None = None
    change_pct: float | None = None

    model_config = {"from_attributes": True}
