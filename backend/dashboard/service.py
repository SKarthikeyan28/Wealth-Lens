import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.accounts.models import Account, Holding
from backend.cashflow.models import Expense
from backend.common.money import round_money
from backend.market.models import Security
from backend.market.service import convert_as_of


async def _position_buckets(
    db: AsyncSession, user_id: uuid.UUID, base_currency: str, as_of: date
) -> dict[str, Decimal]:
    """Value every position in base currency (as-of `as_of`), bucketed by asset
    class. Cash goes to a 'CASH' bucket; holdings to their security's asset class.
    Holdings are valued at COST BASIS (quantity * avg_cost) — market valuation is
    Phase 4. Returns full precision; round at presentation.
    """
    buckets: dict[str, Decimal] = {}

    cash_accounts = await db.scalars(select(Account).where(Account.user_id == user_id))
    for account in cash_accounts:
        value = await convert_as_of(
            db, account.cash_balance, account.currency, base_currency, as_of
        )
        buckets["CASH"] = buckets.get("CASH", Decimal(0)) + value

    holdings = await db.scalars(
        select(Holding)
        .join(Account, Holding.account_id == Account.id)
        .where(Account.user_id == user_id)
    )
    for holding in holdings:
        security = await db.scalar(select(Security).where(Security.id == holding.security_id))
        if security is None:  # FK guarantees presence; defensive only
            continue
        cost_basis = holding.quantity * holding.avg_cost
        value = await convert_as_of(db, cost_basis, security.currency, base_currency, as_of)
        key = security.asset_class.value
        buckets[key] = buckets.get(key, Decimal(0)) + value

    return buckets


async def net_worth(
    db: AsyncSession, user_id: uuid.UUID, base_currency: str, as_of: date
) -> Decimal:
    buckets = await _position_buckets(db, user_id, base_currency, as_of)
    return round_money(sum(buckets.values(), Decimal(0)), base_currency)


async def allocation(
    db: AsyncSession, user_id: uuid.UUID, base_currency: str, as_of: date
) -> tuple[Decimal, list[tuple[str, Decimal, Decimal]]]:
    buckets = await _position_buckets(db, user_id, base_currency, as_of)
    total = sum(buckets.values(), Decimal(0))
    slices: list[tuple[str, Decimal, Decimal]] = []
    for asset_class in sorted(buckets):
        value = buckets[asset_class]
        weight = (value / total) if total > 0 else Decimal(0)
        slices.append(
            (asset_class, round_money(value, base_currency), weight.quantize(Decimal("0.0001")))
        )
    return round_money(total, base_currency), slices


async def expense_summary(
    db: AsyncSession, user_id: uuid.UUID, base_currency: str, start: date, end: date
) -> list[tuple[str, Decimal]]:
    rows = await db.scalars(
        select(Expense).where(
            Expense.user_id == user_id,
            Expense.spent_on >= start,
            Expense.spent_on <= end,
        )
    )
    buckets: dict[str, Decimal] = {}
    for expense in rows:
        # Convert each expense at its OWN spend date (as-of dating per row).
        value = await convert_as_of(
            db, expense.amount, expense.currency, base_currency, expense.spent_on
        )
        buckets[expense.category] = buckets.get(expense.category, Decimal(0)) + value
    return [(cat, round_money(buckets[cat], base_currency)) for cat in sorted(buckets)]
