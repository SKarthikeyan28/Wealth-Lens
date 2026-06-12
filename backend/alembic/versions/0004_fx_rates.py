"""fx rates with as-of dating

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fx_rates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("base_currency", sa.CHAR(3), nullable=False),    # 1 base unit ...
        sa.Column("quote_currency", sa.CHAR(3), nullable=False),   # ... = rate quote units
        sa.Column("rate", sa.Numeric(18, 8), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.CheckConstraint("rate > 0", name="ck_fx_rates_rate"),
        sa.UniqueConstraint("base_currency", "quote_currency", "as_of",
                            name="uq_fx_rates_pair_date"),
    )
    op.create_index(
        "idx_fx_rates_lookup", "fx_rates", ["base_currency", "quote_currency", "as_of"]
    )


def downgrade() -> None:
    op.drop_index("idx_fx_rates_lookup", table_name="fx_rates")
    op.drop_table("fx_rates")
