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
    prev_close: float | None = None
    market_value: float | None
    unrealized_pnl: float | None
    unrealized_pnl_pct: float | None
    day_change: float | None = None
    day_change_pct: float | None = None

    model_config = {"from_attributes": True}


class TradeOut(BaseModel):
    id: int
    symbol: str
    side: Literal["buy", "sell"]
    quantity: int
    price: float
    realized_pnl: float | None = None
    executed_at: datetime

    model_config = {"from_attributes": True}


class PendingSettlementOut(BaseModel):
    amount: float
    settles_at: str


class MarketStatusOut(BaseModel):
    open: bool
    session: Literal["pre", "regular", "post", "closed"]
    next_open_iso: str
    now_iso: str


class PortfolioOut(BaseModel):
    cash: float
    buying_power: float
    pending_settlement: float
    reserved_for_orders: float = 0.0
    pending_settlements: list[PendingSettlementOut] = []
    positions: list[PositionOut]
    market_value: float
    total_value: float
    initial_cash: float = 100000.0
    realized_pnl: float = 0.0
    market_status: MarketStatusOut


class LimitOrderIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    side: Literal["buy", "sell"]
    quantity: int = Field(gt=0)
    limit_price: float = Field(gt=0)


class LimitOrderOut(BaseModel):
    id: int
    symbol: str
    side: Literal["buy", "sell"]
    quantity: int
    limit_price: float
    status: str
    created_at: datetime
    filled_at: datetime | None

    model_config = {"from_attributes": True}
