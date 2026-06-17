import calendar
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.accounts.models import Account, AccountType, Holding
from backend.cashflow.engine import (
    DEFAULT_REAL_RETURN,
    DEFAULT_WITHDRAWAL_RATE,
    CashflowSummary,
    summarize,
)
from backend.cashflow.models import Expense, Income
from backend.common.errors import AppError
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


def _months_back(d: date, months: int) -> date:
    """The date `months` calendar months before `d`, clamping the day to the
    target month's length (so 31 Mar - 1 month = 28/29 Feb, never an invalid date)."""
    total = d.year * 12 + (d.month - 1) - months
    year, month = divmod(total, 12)
    month += 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


async def _sum_income(
    db: AsyncSession, user_id: uuid.UUID, base_currency: str, start: date, end: date
) -> Decimal:
    """Total income in [start, end], each entry converted at its OWN receipt date.
    Full precision — the caller annualises and the router rounds at presentation."""
    rows = await db.scalars(
        select(Income).where(
            Income.user_id == user_id,
            Income.received_on >= start,
            Income.received_on <= end,
        )
    )
    total = Decimal(0)
    for income in rows:
        total += await convert_as_of(
            db, income.amount, income.currency, base_currency, income.received_on
        )
    return total


async def _sum_expenses(
    db: AsyncSession, user_id: uuid.UUID, base_currency: str, start: date, end: date
) -> Decimal:
    """Total expenses in [start, end], each converted at its OWN spend date."""
    rows = await db.scalars(
        select(Expense).where(
            Expense.user_id == user_id,
            Expense.spent_on >= start,
            Expense.spent_on <= end,
        )
    )
    total = Decimal(0)
    for expense in rows:
        total += await convert_as_of(
            db, expense.amount, expense.currency, base_currency, expense.spent_on
        )
    return total


async def _liquid_assets(
    db: AsyncSession, user_id: uuid.UUID, base_currency: str, as_of: date
) -> Decimal:
    """Cash in CASH-type accounts only (for emergency runway). CPF/SRS are locked,
    so they count toward net worth but NOT toward liquid runway."""
    accounts = await db.scalars(
        select(Account).where(
            Account.user_id == user_id,
            Account.account_type == AccountType.CASH,
        )
    )
    total = Decimal(0)
    for account in accounts:
        total += await convert_as_of(
            db, account.cash_balance, account.currency, base_currency, as_of
        )
    return total


# CPF and SRS are locked until statutory retirement, so they can't fund FI before
# then — excluded from the years-to-FI starting capital (but still in net worth).
LOCKED_ACCOUNT_TYPES = frozenset(
    {AccountType.CPF_OA, AccountType.CPF_SA, AccountType.CPF_MA, AccountType.SRS}
)


async def _investable_assets(
    db: AsyncSession, user_id: uuid.UUID, base_currency: str, as_of: date
) -> Decimal:
    """Net worth EXCLUDING locked CPF/SRS — the capital actually available to reach
    FI before retirement: cash and holdings (at cost basis) in non-locked accounts."""
    total = Decimal(0)
    accounts = await db.scalars(
        select(Account).where(
            Account.user_id == user_id,
            Account.account_type.notin_(LOCKED_ACCOUNT_TYPES),
        )
    )
    for account in accounts:
        total += await convert_as_of(
            db, account.cash_balance, account.currency, base_currency, as_of
        )
    holdings = await db.scalars(
        select(Holding)
        .join(Account, Holding.account_id == Account.id)
        .where(
            Account.user_id == user_id,
            Account.account_type.notin_(LOCKED_ACCOUNT_TYPES),
        )
    )
    for holding in holdings:
        security = await db.scalar(select(Security).where(Security.id == holding.security_id))
        if security is None:  # FK guarantees presence; defensive only
            continue
        cost_basis = holding.quantity * holding.avg_cost
        total += await convert_as_of(db, cost_basis, security.currency, base_currency, as_of)
    return total


async def cashflow_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
    base_currency: str,
    as_of: date,
    months: int = 12,
    withdrawal_rate: Decimal = DEFAULT_WITHDRAWAL_RATE,
    annual_real_return: Decimal = DEFAULT_REAL_RETURN,
) -> CashflowSummary:
    """Aggregate a trailing-`months` window (income/expenses FX-normalised per row)
    plus investable assets, then feed the pure cash-flow engine. Returns FULL
    PRECISION; the router rounds money fields at presentation."""
    if months <= 0:
        raise AppError("INVALID_WINDOW", "months must be a positive integer.", 422)
    start = _months_back(as_of, months)

    window_income = await _sum_income(db, user_id, base_currency, start, as_of)
    window_expenses = await _sum_expenses(db, user_id, base_currency, start, as_of)

    # Annualise so the engine always sees yearly figures, even for a non-12 window.
    factor = Decimal(12) / Decimal(months)
    annual_income = window_income * factor
    annual_expenses = window_expenses * factor
    monthly_expenses = window_expenses / Decimal(months)

    liquid_assets = await _liquid_assets(db, user_id, base_currency, as_of)
    current_assets = await _investable_assets(db, user_id, base_currency, as_of)

    return summarize(
        annual_income=annual_income,
        annual_expenses=annual_expenses,
        monthly_expenses=monthly_expenses,
        liquid_assets=liquid_assets,
        current_assets=current_assets,
        withdrawal_rate=withdrawal_rate,
        annual_real_return=annual_real_return,
    )
