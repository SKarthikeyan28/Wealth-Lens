"""Hand-verified tests for the goal Monte-Carlo engine.

Anchors:
- Zero-volatility collapses to the deterministic future-value annuity.
- Same seed -> identical arrays (reproducibility); different seeds -> different.
- The gate: at large N two seeds agree (Monte-Carlo convergence).
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
import pytest

from backend.montecarlo.engine import (
    percentile_bands,
    probability_of_goal,
    simulate_paths,
    terminal_wealth,
)

# Deterministic FV anchor (volatility = 0):
#   (1.05)^10 = 1.6288946268
#   W10 = 100000*1.6288946268 + 10000*(1.6288946268-1)/0.05 = 288668.39
FV_W10 = 288668.39


def _paths(*, seed: int, n_sims: int = 500) -> npt.NDArray[np.float64]:
    """Standard stochastic run (vol 0.15) shared by reproducibility/convergence."""
    return simulate_paths(
        initial_wealth=100000.0,
        annual_contribution=10000.0,
        mean_return=0.06,
        volatility=0.15,
        years=10,
        n_sims=n_sims,
        seed=seed,
    )


def test_zero_volatility_matches_future_value_annuity() -> None:
    paths = simulate_paths(
        initial_wealth=100000,
        annual_contribution=10000,
        mean_return=0.05,
        volatility=0.0,
        years=10,
        n_sims=50,
        seed=0,
    )
    term = terminal_wealth(paths)
    assert np.allclose(term, FV_W10, atol=0.1)


def test_probability_zero_volatility_is_deterministic() -> None:
    paths = simulate_paths(
        initial_wealth=100000,
        annual_contribution=10000,
        mean_return=0.05,
        volatility=0.0,
        years=10,
        n_sims=50,
        seed=0,
    )
    assert probability_of_goal(paths, goal=250000) == 1.0
    assert probability_of_goal(paths, goal=300000) == 0.0


def test_reproducibility_same_seed_equal_different_seed_not() -> None:
    a = _paths(seed=1)
    b = _paths(seed=1)
    c = _paths(seed=2)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_shape_and_initial_column() -> None:
    paths = simulate_paths(
        initial_wealth=100000,
        annual_contribution=10000,
        mean_return=0.06,
        volatility=0.15,
        years=10,
        n_sims=500,
        seed=7,
    )
    assert paths.shape == (500, 11)
    assert np.all(paths[:, 0] == 100000)


def test_probability_bounds() -> None:
    paths = simulate_paths(
        initial_wealth=100000,
        annual_contribution=10000,
        mean_return=0.06,
        volatility=0.15,
        years=10,
        n_sims=500,
        seed=7,
    )
    p_mid = probability_of_goal(paths, goal=350000)
    assert 0.0 <= p_mid <= 1.0
    assert probability_of_goal(paths, goal=0) == 1.0
    assert probability_of_goal(paths, goal=1e15) == 0.0


def test_percentile_bands_ordering_and_length() -> None:
    paths = simulate_paths(
        initial_wealth=100000,
        annual_contribution=10000,
        mean_return=0.06,
        volatility=0.15,
        years=10,
        n_sims=2000,
        seed=3,
    )
    bands = percentile_bands(paths)
    for band in bands.values():
        assert band.shape == (11,)
    # At the final year the percentiles must be monotone non-decreasing.
    p10, p25, p50, p75, p90 = (bands[q][-1] for q in (10, 25, 50, 75, 90))
    assert p10 <= p25 <= p50 <= p75 <= p90


def test_monte_carlo_convergence_seed_independence_at_large_n() -> None:
    # The gate: two independent large-N runs (different seeds) estimate the same
    # probability to within Monte-Carlo error. Demonstrates convergence; a small-N
    # run is NOT required to match (and intentionally isn't asserted to).
    goal = 350000
    p1 = probability_of_goal(_paths(seed=1, n_sims=20000), goal)
    p2 = probability_of_goal(_paths(seed=2, n_sims=20000), goal)
    assert p1 == pytest.approx(p2, abs=0.03)


def test_validation_errors() -> None:
    with pytest.raises(ValueError):  # years < 1
        simulate_paths(
            initial_wealth=100000.0, annual_contribution=10000.0, mean_return=0.06,
            volatility=0.15, years=0, n_sims=10, seed=0,
        )
    with pytest.raises(ValueError):  # n_sims < 1
        simulate_paths(
            initial_wealth=100000.0, annual_contribution=10000.0, mean_return=0.06,
            volatility=0.15, years=10, n_sims=0, seed=0,
        )
    with pytest.raises(ValueError):  # volatility < 0
        simulate_paths(
            initial_wealth=100000.0, annual_contribution=10000.0, mean_return=0.06,
            volatility=-0.1, years=10, n_sims=10, seed=0,
        )
