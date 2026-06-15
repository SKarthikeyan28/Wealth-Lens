"""Market-math engine: returns, covariance, correlation.

Pure functions — no DB, no Redis, no I/O. This is the verifiable core that the
CRRA optimiser (4.3), efficient frontier (4.4), and Monte Carlo (4.5) all reuse.

The Decimal/float boundary: prices arrive here as float64 (the caller converts
from Decimal at the loader edge). Returns and covariances are *statistical
estimates*, not ledger values, so they live in float64 — Decimal would buy false
precision and break numpy/cvxpy. Money stays Decimal; statistics are float.

Array convention: a returns/price matrix is shaped (T, N) — rows are time
observations, columns are assets. This matches numpy's `rowvar=False`.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

#: Trading days in a year — the standard scaling factor for daily data.
TRADING_DAYS_PER_YEAR = 252

FloatArray = npt.NDArray[np.float64]


def simple_returns(prices: FloatArray) -> FloatArray:
    """Simple returns P_t / P_{t-1} - 1.

    Correct unit for *cross-sectional* aggregation: a portfolio's return is the
    weighted average of its holdings' simple returns. `prices` is (T,) or (T, N);
    the result has one fewer row.
    """
    p = np.asarray(prices, dtype=np.float64)
    return p[1:] / p[:-1] - 1.0


def log_returns(prices: FloatArray) -> FloatArray:
    """Log returns ln(P_t / P_{t-1}).

    Time-additive (the log return over a span is the *sum* of sub-period log
    returns) and closer to normal, so this is the unit we feed to covariance.
    """
    p = np.asarray(prices, dtype=np.float64)
    return np.asarray(np.log(p[1:] / p[:-1]), dtype=np.float64)


def covariance_matrix(returns: FloatArray, *, ddof: int = 1) -> FloatArray:
    """Sample covariance of a (T, N) returns array (rows = observations).

    ddof=1 divides by T-1 (Bessel's correction): we estimate from a sample, not
    the whole population. The diagonal is each asset's variance; off-diagonals
    are the co-movement that diversification exploits.
    """
    r = np.asarray(returns, dtype=np.float64)
    return np.asarray(np.cov(r, rowvar=False, ddof=ddof), dtype=np.float64)


def correlation_matrix(returns: FloatArray) -> FloatArray:
    """Pearson correlation of a (T, N) returns array: covariance normalised to
    [-1, 1] by the assets' standard deviations. Same information as covariance,
    unit-free and easy to sanity-check."""
    r = np.asarray(returns, dtype=np.float64)
    return np.asarray(np.corrcoef(r, rowvar=False), dtype=np.float64)


def annualize_covariance(
    cov: FloatArray, *, periods_per_year: int = TRADING_DAYS_PER_YEAR
) -> FloatArray:
    """Scale a per-period covariance matrix to annual. Under the i.i.d.
    assumption variance grows linearly with time, so covariance scales by the
    number of periods per year (252 for daily)."""
    return np.asarray(cov, dtype=np.float64) * periods_per_year


def annualize_log_return(
    mean_log_return: FloatArray, *, periods_per_year: int = TRADING_DAYS_PER_YEAR
) -> FloatArray:
    """Annualise a mean per-period *log* return by summation — valid precisely
    because log returns are time-additive: r_annual = r_period * periods_per_year.
    (Simple returns would instead compound: (1+r)^periods - 1.)"""
    return np.asarray(mean_log_return, dtype=np.float64) * periods_per_year
