import enum
import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import CHAR, CheckConstraint, ForeignKey, Numeric, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.database import Base


class AccountType(str, enum.Enum):
    CASH = "CASH"
    BROKERAGE = "BROKERAGE"
    CPF_OA = "CPF_OA"
    CPF_SA = "CPF_SA"
    CPF_MA = "CPF_MA"
    SRS = "SRS"


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint("cash_balance >= 0", name="ck_accounts_cash_balance"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    account_type: Mapped[AccountType] = mapped_column(
        sa.Enum(AccountType, name="account_type", create_type=False), nullable=False
    )
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default="SGD")
    cash_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Holding(Base):
    __tablename__ = "holdings"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_holdings_quantity"),
        CheckConstraint("avg_cost >= 0", name="ck_holdings_avg_cost"),
        sa.UniqueConstraint("account_id", "security_id", name="uq_holdings_account_security"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    security_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("securities.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    avg_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
