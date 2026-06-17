import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.database import Base


class RiskProfile(Base):
    __tablename__ = "risk_profile"
    __table_args__ = (
        CheckConstraint("crra_gamma > 0", name="ck_risk_profile_crra_gamma"),
        CheckConstraint("crra_gamma_low >= 0", name="ck_risk_profile_gamma_low"),
        CheckConstraint(
            "crra_gamma_high >= crra_gamma_low", name="ck_risk_profile_gamma_band"
        ),
        sa.UniqueConstraint("user_id", name="uq_risk_profile_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    crra_gamma: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    crra_gamma_low: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    crra_gamma_high: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(server_default=func.now())
