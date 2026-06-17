from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class NetWorthResponse(BaseModel):
    base_currency: str
    as_of: date
    total: Decimal


class AllocationSlice(BaseModel):
    asset_class: str
    value: Decimal
    weight: Decimal


class AllocationResponse(BaseModel):
    base_currency: str
    as_of: date
    total: Decimal
    slices: list[AllocationSlice]


class ExpenseSummarySlice(BaseModel):
    category: str
    total: Decimal


class ExpenseSummaryResponse(BaseModel):
    base_currency: str
    start: date
    end: date
    slices: list[ExpenseSummarySlice]


class CashflowSummaryResponse(BaseModel):
    base_currency: str
    as_of: date
    window_months: int
    savings_rate: Decimal | None       # fraction, e.g. 0.4000 = 40%
    monthly_expenses: Decimal
    runway_months: Decimal | None      # None == no expenses (unbounded)
    annual_expenses: Decimal
    fi_number: Decimal
    years_to_fi: float | None          # None == target never reached
    # Assumptions echoed so the UI can surface exactly how the projection was made.
    withdrawal_rate: Decimal
    annual_real_return: Decimal
