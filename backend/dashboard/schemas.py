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
