import numpy as np
import pytest

from backend.crra import optimizer

# Two uncorrelated assets:
#   A: mu=0.10, var=0.04  (high return, high risk)
#   B: mu=0.04, var=0.01  (low return, low risk)
# Sigma is diagonal because they are uncorrelated.
MU = np.array([0.10, 0.04])
SIGMA = np.array([[0.04, 0.0], [0.0, 0.01]])

# Closed-form long-only interior optimum weight on A:
#   x = ((muA - muB)/gamma + varB) / (varA + varB)
#     = (0.06/gamma + 0.01) / 0.05


def test_optimal_weights_gamma_3() -> None:
    # x = (0.06/3 + 0.01)/0.05 = (0.02 + 0.01)/0.05 = 0.6
    w = optimizer.optimal_weights(MU, SIGMA, 3.0)
    assert w[0] == pytest.approx(0.6, abs=1e-2)
    assert w[1] == pytest.approx(0.4, abs=1e-2)


def test_optimal_weights_gamma_6() -> None:
    # x = (0.06/6 + 0.01)/0.05 = (0.01 + 0.01)/0.05 = 0.4
    w = optimizer.optimal_weights(MU, SIGMA, 6.0)
    assert w[0] == pytest.approx(0.4, abs=1e-2)
    assert w[1] == pytest.approx(0.6, abs=1e-2)


def test_constraints_always_hold() -> None:
    for gamma in (0.5, 3.0, 6.0, 12.0):
        w = optimizer.optimal_weights(MU, SIGMA, gamma)
        assert w.sum() == pytest.approx(1.0, abs=1e-2)
        assert np.all(w >= -1e-6)  # long-only


def test_risk_aversion_shifts_to_safe_asset() -> None:
    # Weight on the RISKY asset A strictly falls as gamma rises.
    w_low = optimizer.optimal_weights(MU, SIGMA, 3.0)
    w_mid = optimizer.optimal_weights(MU, SIGMA, 6.0)
    w_high = optimizer.optimal_weights(MU, SIGMA, 12.0)
    assert w_high[0] < w_mid[0] < w_low[0]


def test_low_gamma_corner_solution() -> None:
    # With almost no risk penalty, the optimiser piles into the high-return asset.
    w = optimizer.optimal_weights(MU, SIGMA, 0.5)
    assert w[0] >= 0.99


def test_portfolio_return_hand_checked() -> None:
    assert optimizer.portfolio_return(np.array([0.6, 0.4]), MU) == pytest.approx(
        0.6 * 0.10 + 0.4 * 0.04
    )


def test_portfolio_variance_hand_checked() -> None:
    assert optimizer.portfolio_variance(np.array([0.6, 0.4]), SIGMA) == pytest.approx(
        0.6**2 * 0.04 + 0.4**2 * 0.01
    )


def test_dimension_mismatch_raises() -> None:
    bad_sigma = np.array([[0.04, 0.0, 0.0], [0.0, 0.01, 0.0], [0.0, 0.0, 0.02]])
    with pytest.raises(ValueError):
        optimizer.optimal_weights(MU, bad_sigma, 3.0)
