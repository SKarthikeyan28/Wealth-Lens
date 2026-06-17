import math
from decimal import Decimal

import pytest

from backend.cashflow.engine import (
    CashflowSummary,
    emergency_runway_months,
    fi_number,
    savings_rate,
    summarize,
    years_to_fi,
)


def test_savings_rate_worked() -> None:
    assert savings_rate(Decimal("5000"), Decimal("3000")) == Decimal("0.4")


def test_savings_rate_negative_when_overspending() -> None:
    assert savings_rate(Decimal("3000"), Decimal("4500")) == Decimal("-0.5")


def test_savings_rate_none_without_income() -> None:
    assert savings_rate(Decimal("0"), Decimal("1000")) is None


def test_runway_worked() -> None:
    assert emergency_runway_months(Decimal("18000"), Decimal("3000")) == Decimal("6")


def test_runway_none_without_expenses() -> None:
    assert emergency_runway_months(Decimal("10000"), Decimal("0")) is None


def test_fi_number_is_25x_at_four_percent() -> None:
    assert fi_number(Decimal("36000")) == Decimal("900000")


def test_fi_number_rejects_nonpositive_rate() -> None:
    with pytest.raises(ValueError):
        fi_number(Decimal("36000"), Decimal("0"))


def test_years_to_fi_zero_return_is_linear() -> None:
    # (900000 - 100000) / 20000 = 40 years exactly
    t = years_to_fi(Decimal("100000"), Decimal("20000"), Decimal("900000"), Decimal("0"))
    assert t == pytest.approx(40.0)


def test_years_to_fi_with_growth_matches_hand_value() -> None:
    # ln(2.6)/ln(1.05) = 19.5841
    t = years_to_fi(Decimal("100000"), Decimal("20000"), Decimal("900000"), Decimal("0.05"))
    assert t == pytest.approx(19.5841, abs=1e-3)


def test_years_to_fi_already_reached() -> None:
    assert years_to_fi(Decimal("900000"), Decimal("0"), Decimal("900000")) == 0.0


def test_years_to_fi_unreachable_returns_none() -> None:
    # No contributions, no growth, below target -> never.
    assert years_to_fi(Decimal("100000"), Decimal("0"), Decimal("900000"), Decimal("0")) is None


def test_summarize_composes_consistently() -> None:
    s = summarize(
        annual_income=Decimal("60000"),
        annual_expenses=Decimal("36000"),
        monthly_expenses=Decimal("3000"),
        liquid_assets=Decimal("18000"),
        current_assets=Decimal("100000"),
    )
    assert isinstance(s, CashflowSummary)
    assert s.savings_rate == Decimal("0.4")        # (60000-36000)/60000
    assert s.runway_months == Decimal("6")
    assert s.fi_number == Decimal("900000")
    # contribution = 60000 - 36000 = 24000; equals the standalone call
    assert s.years_to_fi == years_to_fi(
        Decimal("100000"), Decimal("24000"), Decimal("900000"), Decimal("0.05")
    )
    assert s.years_to_fi is not None and math.isfinite(s.years_to_fi)
