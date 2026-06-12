"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enum types, declared once. create_type=False means create_table() will NOT
# auto-create them — we create them explicitly (idempotently) in upgrade(), and
# reference these same objects in the columns below.
account_type = postgresql.ENUM(
    "CASH", "BROKERAGE", "CPF_OA", "CPF_SA", "CPF_MA", "SRS",
    name="account_type", create_type=False,
)
asset_class = postgresql.ENUM(
    "EQUITY", "ETF", "REIT", "BOND", "PRECIOUS_METAL", "CASH_EQUIVALENT",
    name="asset_class", create_type=False,
)
income_source = postgresql.ENUM(
    "SALARY", "BONUS", "DIVIDEND", "MISC",
    name="income_source", create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Enum types — created before the tables that use them. checkfirst avoids
    # a duplicate-type error if a type already exists from a prior partial run.
    bind = op.get_bind()
    account_type.create(bind, checkfirst=True)
    asset_class.create(bind, checkfirst=True)
    income_source.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("totp_secret", sa.Text(), nullable=True),
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("consumed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )

    op.create_table(
        "recovery_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code_hash", sa.Text(), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("account_type", account_type, nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False, server_default="SGD"),
        sa.Column("cash_balance", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("cash_balance >= 0", name="ck_accounts_cash_balance"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_accounts_user", "accounts", ["user_id"])

    op.create_table(
        "securities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("asset_class", asset_class, nullable=False),
        sa.Column("exchange", sa.Text(), nullable=True),
        sa.Column("currency", sa.CHAR(3), nullable=False),
        sa.UniqueConstraint("ticker", "exchange", name="uq_securities_ticker_exchange"),
    )

    op.create_table(
        "holdings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("security_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("avg_cost", sa.Numeric(18, 6), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("quantity >= 0", name="ck_holdings_quantity"),
        sa.CheckConstraint("avg_cost >= 0", name="ck_holdings_avg_cost"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["security_id"], ["securities.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("account_id", "security_id", name="uq_holdings_account_security"),
    )
    op.create_index("idx_holdings_account", "holdings", ["account_id"])
    op.create_index("idx_holdings_security", "holdings", ["security_id"])

    op.create_table(
        "price_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("security_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("price_date", sa.Date(), nullable=False),
        sa.Column("close_price", sa.Numeric(18, 6), nullable=False),
        sa.CheckConstraint("close_price >= 0", name="ck_price_history_close_price"),
        sa.ForeignKeyConstraint(["security_id"], ["securities.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("security_id", "price_date", name="uq_price_history_security_date"),
    )
    op.create_index("idx_price_security_date", "price_history", ["security_id", "price_date"])

    op.create_table(
        "income",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", income_source, nullable=False, server_default="SALARY"),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False, server_default="SGD"),
        sa.Column("received_on", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.CheckConstraint("amount >= 0", name="ck_income_amount"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_income_user_date", "income", ["user_id", "received_on"])

    op.create_table(
        "expenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False, server_default="SGD"),
        sa.Column("spent_on", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.CheckConstraint("amount >= 0", name="ck_expenses_amount"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_expenses_user_date", "expenses", ["user_id", "spent_on"])
    op.create_index("idx_expenses_user_category", "expenses", ["user_id", "category"])

    op.create_table(
        "goals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("target_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False, server_default="SGD"),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("target_amount > 0", name="ck_goals_target_amount"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_goals_user", "goals", ["user_id"])

    op.create_table(
        "risk_profile",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("crra_gamma", sa.Numeric(6, 3), nullable=False),
        sa.Column("assessed_at", sa.TIMESTAMP(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("crra_gamma > 0", name="ck_risk_profile_crra_gamma"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_risk_profile_user"),
    )

    # updated_at trigger — keeps users.updated_at current on every UPDATE.
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW EXECUTE FUNCTION set_updated_at()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_users_updated_at ON users")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at")

    op.drop_table("risk_profile")
    op.drop_index("idx_goals_user", table_name="goals")
    op.drop_table("goals")
    op.drop_index("idx_expenses_user_category", table_name="expenses")
    op.drop_index("idx_expenses_user_date", table_name="expenses")
    op.drop_table("expenses")
    op.drop_index("idx_income_user_date", table_name="income")
    op.drop_table("income")
    op.drop_index("idx_price_security_date", table_name="price_history")
    op.drop_table("price_history")
    op.drop_index("idx_holdings_security", table_name="holdings")
    op.drop_index("idx_holdings_account", table_name="holdings")
    op.drop_table("holdings")
    op.drop_table("securities")
    op.drop_index("idx_accounts_user", table_name="accounts")
    op.drop_table("accounts")
    op.drop_table("recovery_codes")
    op.drop_table("refresh_tokens")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS income_source")
    op.execute("DROP TYPE IF EXISTS asset_class")
    op.execute("DROP TYPE IF EXISTS account_type")
