import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import CHAR, CheckConstraint, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.database import Base


class AssetClass(str, enum.Enum):
    EQUITY = "EQUITY"
    ETF = "ETF"
    REIT = "REIT"
    BOND = "BOND"
    PRECIOUS_METAL = "PRECIOUS_METAL"
    CASH_EQUIVALENT = "CASH_EQUIVALENT"


class Security(Base):
    __tablename__ = "securities"
    __table_args__ = (
        sa.UniqueConstraint("ticker", "exchange", name="uq_securities_ticker_exchange"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_class: Mapped[AssetClass] = mapped_column(
        sa.Enum(AssetClass, name="asset_class", create_type=False), nullable=False
    )
    exchange: Mapped[str | None] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)


class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = (
        CheckConstraint("close_price >= 0", name="ck_price_history_close_price"),
        sa.UniqueConstraint("security_id", "price_date", name="uq_price_history_security_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    security_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("securities.id", ondelete="CASCADE"), nullable=False
    )
    price_date: Mapped[date] = mapped_column(sa.Date(), nullable=False)
    close_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
