"""add created_at to price_history (model/schema drift fix)

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The ORM model has always declared created_at, but the table in 0001 omitted
    # it. Harmless until the first INSERT — backfill existing rows with now().
    op.add_column(
        "price_history",
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("price_history", "created_at")
