from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.models import User
from backend.cashflow.engine import DEFAULT_REAL_RETURN, DEFAULT_WITHDRAWAL_RATE
from backend.common.database import get_db
from backend.common.money import round_money
from backend.dashboard.schemas import (
    AllocationResponse,
    AllocationSlice,
    CashflowSummaryResponse,
    ExpenseSummaryResponse,
    ExpenseSummarySlice,
    NetWorthResponse,
)
from backend.dashboard.service import (
    allocation,
    cashflow_summary,
    expense_summary,
    net_worth,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/net-worth", response_model=NetWorthResponse)
async def get_net_worth(
    base: str = "SGD",
    as_of: date | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NetWorthResponse:
    on = as_of or date.today()
    total = await net_worth(db, user.id, base.upper(), on)
    return NetWorthResponse(base_currency=base.upper(), as_of=on, total=total)


@router.get("/allocation", response_model=AllocationResponse)
async def get_allocation(
    base: str = "SGD",
    as_of: date | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AllocationResponse:
    on = as_of or date.today()
    total, slices = await allocation(db, user.id, base.upper(), on)
    return AllocationResponse(
        base_currency=base.upper(),
        as_of=on,
        total=total,
        slices=[AllocationSlice(asset_class=a, value=v, weight=w) for a, v, w in slices],
    )


@router.get("/expenses", response_model=ExpenseSummaryResponse)
async def get_expense_summary(
    start: date,
    end: date,
    base: str = "SGD",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExpenseSummaryResponse:
    rows = await expense_summary(db, user.id, base.upper(), start, end)
    return ExpenseSummaryResponse(
        base_currency=base.upper(),
        start=start,
        end=end,
        slices=[ExpenseSummarySlice(category=c, total=t) for c, t in rows],
    )


@router.get("/cashflow-summary", response_model=CashflowSummaryResponse)
async def get_cashflow_summary(
    base: str = "SGD",
    as_of: date | None = None,
    months: int = 12,
    withdrawal_rate: Decimal = DEFAULT_WITHDRAWAL_RATE,
    annual_real_return: Decimal = DEFAULT_REAL_RETURN,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CashflowSummaryResponse:
    on = as_of or date.today()
    currency = base.upper()
    s = await cashflow_summary(
        db, user.id, currency, on, months, withdrawal_rate, annual_real_return
    )
    # Presentation boundary: round money to minor units, ratios to fixed dp.
    return CashflowSummaryResponse(
        base_currency=currency,
        as_of=on,
        window_months=months,
        savings_rate=(
            s.savings_rate.quantize(Decimal("0.0001")) if s.savings_rate is not None else None
        ),
        monthly_expenses=round_money(s.monthly_expenses, currency),
        runway_months=(
            s.runway_months.quantize(Decimal("0.1")) if s.runway_months is not None else None
        ),
        annual_expenses=round_money(s.annual_expenses, currency),
        fi_number=round_money(s.fi_number, currency),
        years_to_fi=(round(s.years_to_fi, 1) if s.years_to_fi is not None else None),
        withdrawal_rate=withdrawal_rate,
        annual_real_return=annual_real_return,
    )
