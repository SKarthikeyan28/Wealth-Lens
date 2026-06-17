"""CRRA engine: utility, certainty equivalent, mean-variance CE return.

Pure functions — no DB, no I/O, no cvxpy. This is the verifiable core that the
risk-aware optimiser (4.3c) maximises.

CRRA = Constant Relative Risk Aversion. A single parameter gamma (>= 0) captures
how much an investor dislikes risk: gamma=0 is risk-neutral (only the mean
matters), and larger gamma penalises uncertainty more steeply. The utility is

    U(W) = W**(1-gamma) / (1-gamma)        (gamma != 1)
    U(W) = ln(W)                           (gamma == 1, the limiting case)

"Constant relative" means doubling wealth scales risk attitude the same way at
every level — the right shape for proportional financial decisions.

The Decimal/float boundary: everything here lives in float64. These are powers,
logs and expectations over *assumed* return distributions — projections, not
ledger values — so Decimal would buy false precision and break numpy. Money
stays Decimal at the edges; this engine is statistics. (Consistent with
`market/analytics.py` and the float half of `cashflow/engine.py`.)

Note: gamma == 1 is a removable singularity of U(W) (the 1/(1-gamma) factor
blows up); we handle it explicitly as the log-utility limit throughout.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np


def crra_utility(wealth: float, gamma: float) -> float:
    """CRRA utility of a certain wealth level.

    U(W) = W**(1-gamma) / (1-gamma) for gamma != 1; U(W) = ln(W) for gamma == 1
    (the limit as gamma -> 1, where the power form is undefined).

    Wealth must be strictly positive: CRRA is defined only on W > 0 (a
    zero/negative outcome means ruin, where utility is -inf and the model breaks
    down). gamma is the coefficient of relative risk aversion, gamma >= 0.
    """
    if wealth <= 0:
        raise ValueError("wealth must be positive")
    if gamma < 0:
        raise ValueError("gamma must be non-negative")
    if gamma == 1.0:
        return math.log(wealth)
    return float(wealth ** (1.0 - gamma) / (1.0 - gamma))


def certainty_equivalent(
    outcomes: Sequence[float], probabilities: Sequence[float], gamma: float
) -> float:
    """Certainty equivalent of a gamble: the guaranteed wealth that an investor
    with risk aversion gamma values exactly as much as the risky outcomes.

    CE = U^{-1}(E[U(W)]). Inverting the CRRA utility gives a closed form:

        gamma != 1:  CE = (sum_i p_i * W_i**(1-gamma)) ** (1/(1-gamma))
        gamma == 1:  CE = exp(sum_i p_i * ln(W_i))     (the geometric mean)

    For a risk-averse investor (gamma > 0) the CE is below the expected value;
    the gap is the risk premium. At gamma == 0 it equals the expected value
    (risk-neutral). Working in CE units keeps everything in dollars, which is far
    easier to sanity-check than raw utils.

    Validates: equal lengths, every outcome > 0, probabilities summing to ~1.
    """
    if len(outcomes) != len(probabilities):
        raise ValueError("outcomes and probabilities must have the same length")
    w = np.asarray(outcomes, dtype=np.float64)
    p = np.asarray(probabilities, dtype=np.float64)
    if w.size == 0:
        raise ValueError("outcomes must be non-empty")
    if np.any(w <= 0):
        raise ValueError("all outcomes must be positive")
    if abs(float(p.sum()) - 1.0) >= 1e-9:
        raise ValueError("probabilities must sum to 1")
    if gamma < 0:
        raise ValueError("gamma must be non-negative")

    if gamma == 1.0:
        # Geometric mean: exp of the probability-weighted mean log wealth.
        return float(np.exp(np.sum(p * np.log(w))))
    expected_u_factor = float(np.sum(p * w ** (1.0 - gamma)))
    return float(expected_u_factor ** (1.0 / (1.0 - gamma)))


def certainty_equivalent_return(
    expected_return: float, variance: float, gamma: float
) -> float:
    """Mean-variance certainty-equivalent RETURN: the risk-adjusted score a
    mean-variance optimiser maximises (used in 4.3c).

        CE_r = expected_return - 0.5 * gamma * variance

    Why this closed form instead of evaluating CRRA utility directly? It is a
    second-order (Taylor) approximation of the CRRA certainty equivalent in
    *return* space, and it is numerically STABLE: just a subtraction. Computing
    normalised CRRA utility for a large gamma overflows/underflows (W**(1-gamma)
    for big gamma blows up or collapses to zero), and you would then have to
    invert it — fragile. Here the risk penalty is simply (gamma / 2) * variance,
    a clean linear-in-variance term the optimiser can differentiate cheaply.

    The result can go negative when the risk penalty exceeds the expected return
    (a very risk-averse investor facing a volatile asset); that is meaningful and
    stays finite, not an error.
    """
    if gamma < 0:
        raise ValueError("gamma must be non-negative")
    if variance < 0:
        raise ValueError("variance must be non-negative")
    return expected_return - 0.5 * gamma * variance
