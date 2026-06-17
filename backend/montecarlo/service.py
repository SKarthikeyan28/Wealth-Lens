"""Goal-projection service: run the Monte-Carlo engine on the user's data.

This wires the pure `montecarlo.engine` to the user's *risk-optimal* portfolio.
The projection assumes the user holds the mean-variance optimal mix for their
elicited CRRA gamma, so the return distribution's mean/volatility come straight
from `crra.service.optimal_allocation` (reused via its service interface — we do
not reach into crra internals).

The Decimal/float boundary. This is a statistical projection, not a ledger.
Money ENTERS as plain float at this edge and every output is a float: probability,
the assumption returns, the wealth-band values, and the echoed goal/initial/
contribution. They are estimates conditional on the return assumptions, so
Decimal would buy false precision and break numpy — and floats serialize as JSON
numbers, sparing the frontend the Decimal-string trap. This is consistent with
`montecarlo.engine` and `crra.engine`, which are float64 throughout. (The only
Decimal that survives is `alloc.crra_gamma`, which we deliberately do not echo.)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.errors import AppError
from backend.crra import service as crra_service
from backend.montecarlo.engine import (
    percentile_bands,
    probability_of_goal,
    simulate_paths,
)


@dataclass(frozen=True)
class YearBand:
    year: int
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float


@dataclass(frozen=True)
class GoalProjection:
    probability: float  # P(terminal wealth >= goal)
    goal_amount: float
    years: int
    initial_wealth: float
    annual_contribution: float
    mean_return: float  # assumption (from optimal portfolio)
    volatility: float  # assumption
    n_sims: int
    seed: int
    bands: list[YearBand]  # fan chart, one per year 0..years


async def project_goal(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    goal_amount: float,
    years: int,
    initial_wealth: float,
    annual_contribution: float,
    n_sims: int = 10000,
    seed: int = 42,
) -> GoalProjection:
    """Project the probability of reaching a wealth goal via Monte-Carlo.

    Returns are drawn from the user's risk-optimal portfolio's mean/volatility.
    Reproducible: same seed -> identical draws -> identical probability/bands.
    """
    if years < 1:
        raise AppError("INVALID_PROJECTION", "years must be >= 1", 422)
    if n_sims < 1:
        raise AppError("INVALID_PROJECTION", "n_sims must be >= 1", 422)
    if goal_amount < 0:
        raise AppError("INVALID_PROJECTION", "goal_amount must be >= 0", 422)

    # mu/sigma from the user's optimal portfolio over a 5y default window.
    end = date.today()
    start = end.replace(year=end.year - 5)
    alloc = await crra_service.optimal_allocation(db, user_id, start=start, end=end)

    paths = simulate_paths(
        initial_wealth,
        annual_contribution,
        alloc.expected_return,
        alloc.volatility,
        years,
        n_sims,
        seed,
    )
    prob = probability_of_goal(paths, goal_amount)
    band_map = percentile_bands(paths)  # {10:arr, 25:.., ...}; each length years+1
    bands = [
        YearBand(
            year=t,
            p10=float(band_map[10][t]),
            p25=float(band_map[25][t]),
            p50=float(band_map[50][t]),
            p75=float(band_map[75][t]),
            p90=float(band_map[90][t]),
        )
        for t in range(years + 1)
    ]
    return GoalProjection(
        probability=prob,
        goal_amount=goal_amount,
        years=years,
        initial_wealth=initial_wealth,
        annual_contribution=annual_contribution,
        mean_return=alloc.expected_return,
        volatility=alloc.volatility,
        n_sims=n_sims,
        seed=seed,
        bands=bands,
    )
