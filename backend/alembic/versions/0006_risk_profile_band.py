"""add gamma band (low/high) to risk_profile

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 4.3d-1 persists a gamma BAND (low/high) alongside the point estimate. The
    # table is empty today (no code writes it yet), but add with a server_default
    # so the columns stay backfill-safe, then drop the default so future inserts
    # must supply both edges explicitly.
    op.add_column(
        "risk_profile",
        sa.Column("crra_gamma_low", sa.Numeric(6, 3), server_default="0", nullable=False),
    )
    op.add_column(
        "risk_profile",
        sa.Column("crra_gamma_high", sa.Numeric(6, 3), server_default="0", nullable=False),
    )
    op.alter_column("risk_profile", "crra_gamma_low", server_default=None)
    op.alter_column("risk_profile", "crra_gamma_high", server_default=None)
    op.create_check_constraint(
        "ck_risk_profile_gamma_low", "risk_profile", "crra_gamma_low >= 0"
    )
    op.create_check_constraint(
        "ck_risk_profile_gamma_band", "risk_profile", "crra_gamma_high >= crra_gamma_low"
    )


def downgrade() -> None:
    op.drop_constraint("ck_risk_profile_gamma_band", "risk_profile", type_="check")
    op.drop_constraint("ck_risk_profile_gamma_low", "risk_profile", type_="check")
    op.drop_column("risk_profile", "crra_gamma_high")
    op.drop_column("risk_profile", "crra_gamma_low")
