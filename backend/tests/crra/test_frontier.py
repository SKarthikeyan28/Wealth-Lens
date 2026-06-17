"""Hand-verified efficient-frontier tests.

Two uncorrelated assets:
  A: mu=0.10, var=0.04 (vol 0.20)
  B: mu=0.04, var=0.01 (vol 0.10)
mu = [0.10, 0.04], cov = [[0.04, 0], [0, 0.01]].

For uncorrelated assets the global minimum-variance long-only portfolio puts
w_A = varB / (varA + varB) = 0.01 / 0.05 = 0.2 -> w = [0.2, 0.8]:
  return = 0.2*0.10 + 0.8*0.04            = 0.052
  var    = 0.2^2*0.04 + 0.8^2*0.01 = 0.008 -> vol = sqrt(0.008) ~ 0.0894427
The high-return/high-vol end is all-in A: return 0.10, vol 0.20.
"""

import numpy as np
import pytest

from backend.crra.frontier import efficient_frontier, portfolio_point

MU = np.array([0.10, 0.04])
COV = np.array([[0.04, 0.0], [0.0, 0.01]])


def test_portfolio_point_min_variance() -> None:
    r, v = portfolio_point(np.array([0.2, 0.8]), MU, COV)
    assert r == pytest.approx(0.052, abs=1e-9)
    assert v == pytest.approx(0.0894427, abs=1e-6)


def test_frontier_min_variance_endpoint() -> None:
    frontier = efficient_frontier(MU, COV)
    assert frontier
    low = frontier[0]  # lowest volatility = min-variance portfolio
    assert low.volatility == pytest.approx(0.0894427, abs=1e-3)
    assert low.expected_return == pytest.approx(0.052, abs=1e-3)


def test_frontier_max_return_endpoint() -> None:
    frontier = efficient_frontier(MU, COV)
    high = frontier[-1]  # highest volatility = all-in A
    assert high.volatility == pytest.approx(0.20, abs=1e-2)
    assert high.expected_return == pytest.approx(0.10, abs=1e-2)


def test_frontier_monotone() -> None:
    frontier = efficient_frontier(MU, COV)
    prev = -float("inf")
    for p in frontier:
        assert p.expected_return >= prev - 1e-9
        prev = p.expected_return


def test_frontier_weights_valid() -> None:
    frontier = efficient_frontier(MU, COV)
    for p in frontier:
        assert sum(p.weights) == pytest.approx(1.0, abs=1e-6)
        assert all(w >= -1e-9 for w in p.weights)
