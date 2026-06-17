"""Goal Monte-Carlo engine: simulate wealth paths, goal probability, fan chart.

Pure functions — no DB, no I/O, no API. numpy only. This is the verifiable core
behind the "will I hit my goal?" projection (Phase 4.5).

The model. Annual steps. Each year wealth first grows by a random *simple* return
drawn from a Normal distribution, then the year-end contribution is added:

    W[t+1] = W[t] * (1 + r_t) + contribution,   r_t ~ Normal(mean_return, volatility)

Returns are i.i.d. across years and simulations. Reproducibility comes from
`numpy.random.default_rng(seed)` — same seed, same matrix of draws, identical
output. With volatility == 0 the random term vanishes and every path collapses to
the deterministic end-of-period future-value annuity:

    W[Y] = W0*(1+mu)^Y + C*((1+mu)^Y - 1)/mu

which is exactly what `cashflow.engine.years_to_fi` inverts — the zero-vol case is
our sanity anchor.

The Decimal/float boundary. Money enters here as plain float at this edge. The
engine is *statistics over an ASSUMED return distribution*, not a ledger: every
output is an estimate conditional on the mean_return / volatility assumptions, so
Decimal would buy false precision and break numpy. Money stays Decimal at the
service edges; this engine is float64 throughout (consistent with `crra/engine.py`
and the float half of `cashflow/engine.py`).

Honest uncertainty. A single-number projection ("you'll have $X") hides the whole
point: the outcome is a distribution. So we never report one number. We report a
*probability of reaching the goal* and *percentile bands* (the fan chart) — the
spread is the message, not noise to be averaged away.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]


def simulate_paths(
    initial_wealth: float,
    annual_contribution: float,
    mean_return: float,
    volatility: float,
    years: int,
    n_sims: int,
    seed: int,
) -> FloatArray:
    """Simulate wealth paths under the annual grow-then-contribute model.

    Returns an (n_sims, years + 1) array of wealth. Column 0 is initial_wealth for
    every simulation; column t (t >= 1) is wealth at the end of year t. Each year
    applies a Normal(mean_return, volatility) simple return then adds the
    contribution at year end:

        W[:, t+1] = W[:, t] * (1 + r[:, t]) + contribution

    Seeded with `numpy.random.default_rng(seed)` so the draws — and therefore the
    whole array — are reproducible. With volatility == 0 every path equals the
    deterministic future-value annuity.

    Validates years >= 1, n_sims >= 1, volatility >= 0; raises ValueError otherwise.
    """
    if years < 1:
        raise ValueError("years must be >= 1")
    if n_sims < 1:
        raise ValueError("n_sims must be >= 1")
    if volatility < 0:
        raise ValueError("volatility must be non-negative")

    rng = np.random.default_rng(seed)
    # (n_sims, years) matrix of i.i.d. simple returns; std=0 yields a constant mean.
    returns = rng.normal(loc=mean_return, scale=volatility, size=(n_sims, years))

    paths = np.empty((n_sims, years + 1), dtype=np.float64)
    paths[:, 0] = initial_wealth
    for t in range(years):
        paths[:, t + 1] = paths[:, t] * (1.0 + returns[:, t]) + annual_contribution

    return np.asarray(paths, dtype=np.float64)


def probability_of_goal(paths: FloatArray, goal: float) -> float:
    """Fraction of simulations whose TERMINAL wealth (last column) >= goal.

    This is the headline number: an empirical probability in [0, 1] estimating
    P(final wealth >= goal) under the assumed return distribution.
    """
    terminal = paths[:, -1]
    return float(np.mean(terminal >= goal))


def percentile_bands(
    paths: FloatArray, quantiles: tuple[float, ...] = (10, 25, 50, 75, 90)
) -> dict[float, FloatArray]:
    """Per-year percentile of wealth across simulations — the fan chart.

    For each quantile q (a percentile in 0..100), computes the q-th percentile of
    wealth at every year across simulations, giving an array of length years + 1.
    Returns {q: band}. p50 is the median path; the gap between p10 and p90 is the
    visual width of the uncertainty.
    """
    bands: dict[float, FloatArray] = {}
    for q in quantiles:
        band = np.percentile(paths, q, axis=0)
        bands[q] = np.asarray(band, dtype=np.float64)
    return bands


def terminal_wealth(paths: FloatArray) -> FloatArray:
    """Terminal wealth per simulation — the last column of the paths array."""
    return np.asarray(paths[:, -1], dtype=np.float64)
