"""CRRA mean-variance portfolio optimiser.

A quadratic program — no DB, no I/O — that turns the market-math engine's output
(`mu` from annualised returns, `Sigma` from `market.analytics.covariance_matrix`)
into a recommended allocation. We choose weights `w` to maximise the
*certainty-equivalent* of a CRRA investor:

    maximize   mu @ w  -  (gamma / 2) * w^T Sigma w
    subject to sum(w) == 1        (fully invested — the budget constraint)
               w >= 0             (long-only — no shorting, default)

`gamma` is the CRRA coefficient of relative risk aversion (>= 0). The first term
rewards expected return; the second penalises portfolio variance, scaled by how
risk-averse the investor is. Higher gamma weights the penalty more heavily, so
the optimum shifts away from the high-return/high-variance asset toward the
minimum-variance, more-diversified mix. As gamma -> 0 the penalty vanishes and
the optimiser piles into the single highest-return asset (a corner solution).

Why `cp.psd_wrap(Sigma)`: a *sample* covariance estimated from real price data
can have tiny negative eigenvalues from floating-point noise, which would make
cvxpy reject the quadratic form as non-convex. We symmetrise Sigma defensively
and wrap it so the solver treats it as positive semidefinite by assertion. This
reuses the SAME Sigma the market engine produces — no re-estimation here.
"""

from __future__ import annotations

import cvxpy as cp
import numpy as np

from backend.common.errors import AppError
from backend.market.analytics import FloatArray


def optimal_weights(
    expected_returns: FloatArray,
    cov: FloatArray,
    gamma: float,
    *,
    long_only: bool = True,
) -> FloatArray:
    """Solve the CRRA mean-variance QP for the optimal portfolio weights.

    Maximises ``mu @ w - (gamma/2) * w^T Sigma w`` subject to the budget
    constraint ``sum(w) == 1`` and, when ``long_only`` (the default), the
    no-shorting constraint ``w >= 0``. Higher ``gamma`` shifts the solution
    toward the minimum-variance mix; ``gamma`` near 0 concentrates in the
    highest-return asset.

    Sigma is symmetrised and ``psd_wrap``-ed so a sample covariance with tiny
    negative eigenvalues is still accepted as a convex quadratic. After solving,
    sub-tolerance negative weights are clipped to 0 and the vector is
    renormalised to sum to 1.

    Raises ``ValueError`` on dimension mismatch or negative ``gamma``, and
    ``AppError("OPTIMISATION_FAILED", ..., 422)`` if the solver does not
    converge.
    """
    mu = np.asarray(expected_returns, dtype=np.float64)
    sigma = np.asarray(cov, dtype=np.float64)

    n = mu.shape[0]
    if sigma.shape != (n, n):
        raise ValueError(
            f"dimension mismatch: expected_returns has length {n} "
            f"but cov has shape {sigma.shape}"
        )
    if gamma < 0:
        raise ValueError(f"gamma must be >= 0, got {gamma}")

    # Defensive symmetrisation: kills any floating-point asymmetry before we
    # assert positive-semidefiniteness via psd_wrap.
    sigma = (sigma + sigma.T) / 2.0

    w = cp.Variable(n)
    objective = cp.Maximize(mu @ w - 0.5 * gamma * cp.quad_form(w, cp.psd_wrap(sigma)))
    constraints = [cp.sum(w) == 1]
    if long_only:
        constraints.append(w >= 0)

    problem = cp.Problem(objective, constraints)
    # Pin the solver: we ship cvxpy-base + clarabel only (clarabel is cvxpy's
    # default conic solver and the one with ARM wheels), so be explicit rather
    # than relying on auto-selection finding an installed solver.
    problem.solve(solver=cp.CLARABEL)

    if problem.status not in ("optimal", "optimal_inaccurate"):
        raise AppError(
            "OPTIMISATION_FAILED",
            f"portfolio optimisation did not converge (status: {problem.status})",
            422,
        )

    weights = np.asarray(w.value, dtype=np.float64)
    # Solver-tolerance cleanup: clip tiny negatives to 0, then renormalise so the
    # returned weights exactly satisfy the budget constraint.
    if long_only:
        weights = np.clip(weights, 0.0, None)
    total = weights.sum()
    if total > 0:
        weights = weights / total
    return np.asarray(weights, dtype=np.float64)


def portfolio_return(weights: FloatArray, expected_returns: FloatArray) -> float:
    """Expected portfolio return: the weighted average ``w @ mu``."""
    w = np.asarray(weights, dtype=np.float64)
    mu = np.asarray(expected_returns, dtype=np.float64)
    return float(w @ mu)


def portfolio_variance(weights: FloatArray, cov: FloatArray) -> float:
    """Portfolio variance: the quadratic form ``w^T Sigma w``."""
    w = np.asarray(weights, dtype=np.float64)
    sigma = np.asarray(cov, dtype=np.float64)
    return float(w @ sigma @ w)
