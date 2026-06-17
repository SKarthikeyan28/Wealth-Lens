"""The privacy boundary of the chatbot.

`FinancialSummary` is the ONLY representation of a user's finances that ever
leaves this process toward the LLM. By construction it holds DERIVED AGGREGATES
only — net-worth total, allocation weights by asset class, savings rate, runway,
years-to-FI. It never holds raw records, account numbers, transaction
descriptions, names, or emails. Privacy-by-design: you cannot leak a PII field
you never put in the object.

It is built by reusing the dashboard module's aggregate interface, so the
chatbot depends only on already-derived numbers, never on raw tables.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from backend.dashboard.service import allocation, cashflow_summary, net_worth


@dataclass(frozen=True)
class AllocationWeight:
    asset_class: str
    weight: Decimal  # fraction in [0, 1]


@dataclass(frozen=True)
class FinancialSummary:
    """Aggregates only — the allowlist of what the LLM is permitted to see."""

    base_currency: str
    as_of: date
    net_worth: Decimal
    allocation: tuple[AllocationWeight, ...]
    savings_rate: Decimal | None
    monthly_expenses: Decimal
    runway_months: Decimal | None
    years_to_fi: float | None


async def build_summary(
    db: AsyncSession, user_id: uuid.UUID, base_currency: str, as_of: date
) -> FinancialSummary:
    """Assemble the derived summary from the dashboard's aggregate interface.
    Allocation keeps WEIGHTS only (drops absolute per-bucket values) — the least
    sensitive shape that still answers diversification questions."""
    nw = await net_worth(db, user_id, base_currency, as_of)
    _total, slices = await allocation(db, user_id, base_currency, as_of)
    cf = await cashflow_summary(db, user_id, base_currency, as_of)
    return FinancialSummary(
        base_currency=base_currency,
        as_of=as_of,
        net_worth=nw,
        allocation=tuple(AllocationWeight(a, w) for a, _v, w in slices),
        savings_rate=cf.savings_rate,
        monthly_expenses=cf.monthly_expenses,
        runway_months=cf.runway_months,
        years_to_fi=cf.years_to_fi,
    )
