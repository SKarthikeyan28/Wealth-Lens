"""Cash-flow engine: savings rate, emergency runway, FI number, years-to-FI.

Pure functions — no DB, no I/O. The aggregation layer sums income, expenses and
liquid assets, then calls these with plain Decimals; that makes the math trivially
unit-testable against worked numbers (how the gate verifies it).

Decimal/float boundary: savings rate and runway are exact ratios of money, so they
stay Decimal. Years-to-FI solves a compound-interest equation with a logarithm — a
projection built on assumptions (expected return, withdrawal rate), not a ledger
value — so it returns float. Assumptions are explicit parameters, never hidden, so
the UI can surface them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal

# The "4% rule" (Trinity study): a portfolio sustainably funds ~4%/yr of its
# starting value. FI number = annual expenses / withdrawal rate (25x at 4%).
DEFAULT_WITHDRAWAL_RATE = Decimal("0.04")
# Expected REAL (inflation-adjusted) annual return — an assumption, surfaced in UI.
DEFAULT_REAL_RETURN = Decimal("0.05")


def savings_rate(income: Decimal, expenses: Decimal) -> Decimal | None:
    """Fraction of income kept: (income - expenses) / income. None if no income;
    negative when spending exceeds income."""
    if income <= 0:
        return None
    return (income - expenses) / income


def emergency_runway_months(
    liquid_assets: Decimal, monthly_expenses: Decimal
) -> Decimal | None:
    """Months of expenses covered by liquid assets with zero income. None when
    there are no expenses (runway is effectively unbounded)."""
    if monthly_expenses <= 0:
        return None
    return liquid_assets / monthly_expenses


def fi_number(
    annual_expenses: Decimal, withdrawal_rate: Decimal = DEFAULT_WITHDRAWAL_RATE
) -> Decimal:
    """Portfolio size that sustainably funds annual_expenses at the withdrawal
    rate. 36000 / 0.04 = 900000 (25x)."""
    if withdrawal_rate <= 0:
        raise ValueError("withdrawal_rate must be positive")
    return annual_expenses / withdrawal_rate


def years_to_fi(
    current_assets: Decimal,
    annual_contribution: Decimal,
    fi_target: Decimal,
    annual_real_return: Decimal = DEFAULT_REAL_RETURN,
) -> float | None:
    """Years for current_assets — growing at annual_real_return and topped up by
    annual_contribution — to reach fi_target. Solves the future-value annuity:

        target = PV*(1+r)^t + PMT*((1+r)^t - 1)/r
        =>  t = ln[(target + PMT/r) / (PV + PMT/r)] / ln(1+r)

    0.0 if already at/above target; None if never reached. Returns float — it's a
    projection, not a ledger value."""
    pv = float(current_assets)
    pmt = float(annual_contribution)
    r = float(annual_real_return)
    target = float(fi_target)

    if pv >= target:
        return 0.0
    if r == 0:
        return (target - pv) / pmt if pmt > 0 else None

    numer = target + pmt / r
    denom = pv + pmt / r
    if numer <= 0 or denom <= 0:
        return None
    t = math.log(numer / denom) / math.log1p(r)
    return t if math.isfinite(t) and t >= 0 else None


@dataclass(frozen=True)
class CashflowSummary:
    savings_rate: Decimal | None
    monthly_expenses: Decimal
    runway_months: Decimal | None
    annual_expenses: Decimal
    fi_number: Decimal
    years_to_fi: float | None


def summarize(
    *,
    annual_income: Decimal,
    annual_expenses: Decimal,
    monthly_expenses: Decimal,
    liquid_assets: Decimal,
    current_assets: Decimal,
    withdrawal_rate: Decimal = DEFAULT_WITHDRAWAL_RATE,
    annual_real_return: Decimal = DEFAULT_REAL_RETURN,
) -> CashflowSummary:
    """Compose all four metrics. annual_contribution = annual_income - annual_expenses,
    tying the savings rate directly to the FI timeline."""
    target = fi_number(annual_expenses, withdrawal_rate)
    return CashflowSummary(
        savings_rate=savings_rate(annual_income, annual_expenses),
        monthly_expenses=monthly_expenses,
        runway_months=emergency_runway_months(liquid_assets, monthly_expenses),
        annual_expenses=annual_expenses,
        fi_number=target,
        years_to_fi=years_to_fi(
            current_assets, annual_income - annual_expenses, target, annual_real_return
        ),
    )
