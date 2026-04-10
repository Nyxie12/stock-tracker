from pydantic import BaseModel

class QuoteOut(BaseModel):
    c: float
    d: float | None = None
    dp: float | None = None
    h: float | None = None
    l: float | None = None
    o: float | None = None
    pc: float | None = None
    t: int | None = None
