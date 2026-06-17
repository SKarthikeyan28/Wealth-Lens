import math

import pytest

from backend.crra.engine import (
    certainty_equivalent,
    certainty_equivalent_return,
    crra_utility,
)


def test_crra_utility_worked_gamma_two() -> None:
    # W^(1-2)/(1-2) = (1/100)/(-1) = -0.01
    assert crra_utility(100.0, 2.0) == -0.01


def test_crra_utility_log_limit_at_gamma_one() -> None:
    # ln(e) = 1
    assert crra_utility(math.e, 1.0) == pytest.approx(1.0)


def test_certainty_equivalent_risk_neutral_is_expected_value() -> None:
    # gamma=0 -> only the mean matters: 0.5*100 + 0.5*200 = 150
    assert certainty_equivalent([100.0, 200.0], [0.5, 0.5], gamma=0.0) == pytest.approx(150.0)


def test_certainty_equivalent_log_utility_is_geometric_mean() -> None:
    # gamma=1 -> geometric mean = sqrt(100*200) = sqrt(20000) ~= 141.4214
    ce = certainty_equivalent([100.0, 200.0], [0.5, 0.5], gamma=1.0)
    assert ce == pytest.approx(math.sqrt(20000.0))


def test_certainty_equivalent_strictly_decreasing_in_gamma() -> None:
    # More risk aversion -> a smaller guaranteed equivalent for the same gamble.
    ce0 = certainty_equivalent([100.0, 200.0], [0.5, 0.5], gamma=0.0)
    ce1 = certainty_equivalent([100.0, 200.0], [0.5, 0.5], gamma=1.0)
    ce3 = certainty_equivalent([100.0, 200.0], [0.5, 0.5], gamma=3.0)
    assert ce0 > ce1 > ce3
    for ce in (ce0, ce1, ce3):
        assert 100.0 < ce < 200.0


def test_certainty_equivalent_return_worked() -> None:
    # 0.08 - 0.5*3*0.04 = 0.08 - 0.06 = 0.02
    assert certainty_equivalent_return(0.08, 0.04, 3.0) == pytest.approx(0.02)


def test_certainty_equivalent_return_large_gamma_is_finite_and_negative() -> None:
    # 0.08 - 0.5*10*0.04 = 0.08 - 0.20 = -0.12; penalty exceeds return, still stable
    ce = certainty_equivalent_return(0.08, 0.04, 10.0)
    assert ce == pytest.approx(-0.12)
    assert math.isfinite(ce)


def test_certainty_equivalent_rejects_bad_probabilities() -> None:
    with pytest.raises(ValueError):
        certainty_equivalent([100.0, 200.0], [0.5, 0.6], gamma=1.0)


def test_crra_utility_rejects_zero_wealth() -> None:
    with pytest.raises(ValueError):
        crra_utility(0.0, 2.0)


def test_crra_utility_rejects_negative_wealth() -> None:
    with pytest.raises(ValueError):
        crra_utility(-50.0, 2.0)
