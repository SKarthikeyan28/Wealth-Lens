"""csv import: expense dedupe + import receipts

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Fingerprint column for idempotent imports. NULL for manual entries
    # (Postgres treats NULLs as distinct, so manual rows never dedupe).
    op.add_column("expenses", sa.Column("dedupe_hash", sa.Text(), nullable=True))
    op.create_unique_constraint(
        "uq_expenses_user_dedupe", "expenses", ["user_id", "dedupe_hash"]
    )

    op.create_table(
        "import_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),        # e.g. "expenses_csv"
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("inserted", sa.Integer(), nullable=False),
        sa.Column("skipped_duplicates", sa.Integer(), nullable=False),
        sa.Column("failed", sa.Integer(), nullable=False),
        sa.Column("errors", postgresql.JSONB(), nullable=False),  # [{row, error}, ...]
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_import_receipts_user", "import_receipts", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_import_receipts_user", table_name="import_receipts")
    op.drop_table("import_receipts")
    op.drop_constraint("uq_expenses_user_dedupe", "expenses", type_="unique")
    op.drop_column("expenses", "dedupe_hash")
