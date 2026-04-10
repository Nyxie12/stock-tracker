from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class PaperPortfolio(Base):
    __tablename__ = "paper_portfolios"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    cash: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("100000"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    positions: Mapped[list["PaperPosition"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    trades: Mapped[list["PaperTrade"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )


class PaperPosition(Base):
    __tablename__ = "paper_positions"
    __table_args__ = (UniqueConstraint("portfolio_id", "symbol", name="uq_paper_position"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("paper_portfolios.id", ondelete="CASCADE"))
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    avg_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4))

    portfolio: Mapped[PaperPortfolio] = relationship(back_populates="positions")


class PaperTrade(Base):
    __tablename__ = "paper_trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("paper_portfolios.id", ondelete="CASCADE"))
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    side: Mapped[str] = mapped_column(String(8))  # "buy" | "sell"
    quantity: Mapped[int] = mapped_column(Integer)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    executed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    portfolio: Mapped[PaperPortfolio] = relationship(back_populates="trades")
