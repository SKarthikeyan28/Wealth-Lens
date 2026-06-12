from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.models import User
from backend.common.database import get_db
from backend.dashboard.schemas import (
    AllocationResponse,
    AllocationSlice,
    ExpenseSummaryResponse,
    ExpenseSummarySlice,
    NetWorthResponse,
)
from backend.dashboard.service import allocation, expense_summary, net_worth

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
