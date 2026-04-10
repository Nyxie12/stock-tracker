from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TradeIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    quantity: int = Field(gt=0)


class PositionOut(BaseModel):
    symbol: str
    quantity: int
    avg_cost: float
    last_price: float | None
    market_value: float | None
    unrealized_pnl: float | None
    unrealized_pnl_pct: float | None

    model_config = {"from_attributes": True}


class TradeOut(BaseModel):
    id: int
    symbol: str
    side: Literal["buy", "sell"]
    quantity: int
    price: float
    executed_at: datetime

    model_config = {"from_attributes": True}


class PortfolioOut(BaseModel):
    cash: float
    positions: list[PositionOut]
    market_value: float
    total_value: float
    initial_cash: float = 100000.0
