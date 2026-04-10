from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AlertCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    condition: Literal["above", "below"]
    threshold: float = Field(gt=0)


class AlertUpdate(BaseModel):
    active: bool | None = None


class AlertOut(BaseModel):
    id: int
    symbol: str
    condition: Literal["above", "below"]
    threshold: float
    active: bool
    last_triggered_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
