"""Efficient frontier — the long-only mean-variance set.

Pure functions, no DB or I/O. We don't solve a separate frontier program: we
*sweep* the SAME CRRA QP (`optimal_weights`) across a grid of risk-aversion
coefficients `gamma`. Each gamma yields one efficient portfolio — low gamma sits
at the high-return/high-volatility end (piling into the top-return asset), high
gamma at the minimum-variance end. Tracing the grid and sorting by volatility
gives the efficient set the user's optimal allocation lives on.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from backend.crra.optimizer import (
    optimal_weights,
    portfolio_return,
    portfolio_variance,
)
from backend.market.analytics import FloatArray

# Default gamma grid swept to trace the long-only efficient set (low gamma = high
# return/vol end, high gamma = min-variance end). The top end runs to ~316 so the
# high-gamma portfolio converges onto the global minimum-variance corner.
DEFAULT_GAMMAS: tuple[float, ...] = tuple(
    float(g) for g in np.logspace(-1, 2.5, 25)
)  # ~0.1 .. ~316


@dataclass(frozen=True)
class FrontierPoint:
    expected_return: float
    volatility: float
    weights: list[float]


def portfolio_point(
    weights: FloatArray, mu: FloatArray, cov: FloatArray
) -> tuple[float, float]:
    """(expected_return, volatility) of an arbitrary weight vector."""
    r = portfolio_return(weights, mu)
    v = math.sqrt(portfolio_variance(weights, cov))
    return r, v


def efficient_frontier(
    mu: FloatArray, cov: FloatArray, gammas: Sequence[float] = DEFAULT_GAMMAS
) -> list[FrontierPoint]:
    """Trace the long-only efficient frontier by solving the CRRA QP across a grid
    of gammas (reusing optimal_weights). Each gamma yields one efficient portfolio;
    returned sorted by volatility ascending. Deduplicate points that coincide
    (corner solutions repeat at low gamma)."""
    mu_arr = np.asarray(mu, dtype=np.float64)
    cov_arr = np.asarray(cov, dtype=np.float64)
    pts: list[FrontierPoint] = []
    for g in gammas:
        w = optimal_weights(mu_arr, cov_arr, float(g))
        r, v = portfolio_point(w, mu_arr, cov_arr)
        pts.append(
            FrontierPoint(
                expected_return=r,
                volatility=v,
                weights=[float(x) for x in w],
            )
        )
    pts.sort(key=lambda p: p.volatility)
    # Deduplicate coincident points (corner solutions repeat at the low-gamma end).
    deduped: list[FrontierPoint] = []
    for p in pts:
        if deduped:
            prev = deduped[-1]
            if (
                math.isclose(p.volatility, prev.volatility, abs_tol=1e-9)
                and math.isclose(p.expected_return, prev.expected_return, abs_tol=1e-9)
            ):
                continue
        deduped.append(p)
    return deduped
