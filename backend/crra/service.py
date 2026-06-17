import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.accounts.models import Account, Holding
from backend.common.audit import write_audit
from backend.common.errors import AppError
from backend.crra.elicitation import GAMMA_CUT_POINTS, estimate_gamma
from backend.crra.frontier import FrontierPoint, efficient_frontier, portfolio_point
from backend.crra.models import RiskProfile
from backend.crra.optimizer import optimal_weights, portfolio_return, portfolio_variance
from backend.market import service as market_service


def _profile_snapshot(rp: RiskProfile) -> dict[str, object]:
    return {
        "id": str(rp.id),
        "user_id": str(rp.user_id),
        "crra_gamma": str(rp.crra_gamma),
        "crra_gamma_low": str(rp.crra_gamma_low),
        "crra_gamma_high": str(rp.crra_gamma_high),
    }


async def get_risk_profile(db: AsyncSession, user_id: uuid.UUID) -> RiskProfile | None:
    rp: RiskProfile | None = await db.scalar(
        select(RiskProfile).where(RiskProfile.user_id == user_id)
    )
    return rp


async def submit_questionnaire(
    db: AsyncSession, user_id: uuid.UUID, answers: Sequence[bool]
) -> RiskProfile:
    if len(answers) != len(GAMMA_CUT_POINTS):
        raise AppError(
            "INVALID_ASSESSMENT",
            f"Questionnaire requires {len(GAMMA_CUT_POINTS)} answers, got {len(answers)}.",
            422,
        )

    est = estimate_gamma(answers)
    # Decimal boundary: the estimator works in float utility-space; round to 3dp
    # here, where the band crosses into the Numeric(6,3) ledger column.
    gamma_point = Decimal(str(round(est.gamma_point, 3)))
    gamma_low = Decimal(str(round(est.gamma_low, 3)))
    gamma_high = Decimal(str(round(est.gamma_high, 3)))

    rp = await get_risk_profile(db, user_id)
    if rp is None:
        rp = RiskProfile(
            id=uuid.uuid4(),
            user_id=user_id,
            crra_gamma=gamma_point,
            crra_gamma_low=gamma_low,
            crra_gamma_high=gamma_high,
        )
        db.add(rp)
        action = "CREATE"
        old: dict[str, object] | None = None
    else:
        old = _profile_snapshot(rp)
        rp.crra_gamma = gamma_point
        rp.crra_gamma_low = gamma_low
        rp.crra_gamma_high = gamma_high
        action = "UPDATE"

    await write_audit(
        db,
        actor_id=user_id,
        action=action,
        entity_type="risk_profile",
        entity_id=rp.id,
        old_data=old,
        new_data=_profile_snapshot(rp),
    )
    await db.commit()
    return rp


@dataclass(frozen=True)
class AllocationSlice:
    ticker: str
    weight: float


@dataclass(frozen=True)
class OptimalAllocation:
    crra_gamma: Decimal
    expected_return: float
    volatility: float
    slices: list[AllocationSlice]


async def optimal_allocation(
    db: AsyncSession, user_id: uuid.UUID, *, start: date, end: date
) -> OptimalAllocation:
    """Turn the user's elicited CRRA gamma + real price data into a recommended
    long-only mean-variance portfolio over the investable universe."""
    profile = await get_risk_profile(db, user_id)
    if profile is None:
        raise AppError(
            "RISK_PROFILE_NOT_FOUND", "Complete the risk questionnaire first.", 404
        )
    gamma = float(profile.crra_gamma)
    universe = await market_service.investable_universe(db, start, end)
    if not universe:
        raise AppError(
            "NO_PRICE_DATA", "No securities have price history in range.", 422
        )
    ticker_by_id = {s.id: s.ticker for s in universe}
    order_ids, mu, sigma = await market_service.expected_returns_and_covariance(
        db, [s.id for s in universe], start, end
    )
    weights = optimal_weights(mu, sigma, gamma)
    ret = portfolio_return(weights, mu)
    vol = float(np.sqrt(portfolio_variance(weights, sigma)))
    slices = [
        AllocationSlice(ticker=ticker_by_id[sid], weight=float(w))
        for sid, w in zip(order_ids, weights)
    ]
    return OptimalAllocation(
        crra_gamma=profile.crra_gamma,
        expected_return=ret,
        volatility=vol,
        slices=slices,
    )


@dataclass(frozen=True)
class FrontierAnalysis:
    frontier: list[FrontierPoint]
    user_return: float | None  # None if user holds none of the universe
    user_volatility: float | None
    optimal_return: float | None  # the user's gamma-optimal point (None if no profile)
    optimal_volatility: float | None
    crra_gamma: Decimal | None


async def frontier_analysis(
    db: AsyncSession, user_id: uuid.UUID, *, start: date, end: date
) -> FrontierAnalysis:
    """Trace the efficient frontier over the investable universe and locate the
    user's CURRENT (cost-basis-weighted) portfolio plus their gamma-optimal point
    on it. The current point should sit on or below the frontier — you can't beat
    the efficient set's return at a given risk level by holding an off-frontier mix.
    """
    universe = await market_service.investable_universe(db, start, end)
    if not universe:
        raise AppError(
            "NO_PRICE_DATA", "No securities have price history in range.", 422
        )
    order_ids, mu, sigma = await market_service.expected_returns_and_covariance(
        db, [s.id for s in universe], start, end
    )
    frontier = efficient_frontier(mu, sigma)

    # User's current weights over the SAME universe securities, valued at cost
    # basis (quantity * avg_cost), in order_ids order; unheld securities -> 0.
    universe_ids = set(order_ids)
    cost_by_security: dict[uuid.UUID, Decimal] = {}
    holdings = await db.scalars(
        select(Holding)
        .join(Account, Holding.account_id == Account.id)
        .where(Account.user_id == user_id)
    )
    for holding in holdings:
        if holding.security_id not in universe_ids:
            continue
        cost_basis = holding.quantity * holding.avg_cost
        cost_by_security[holding.security_id] = (
            cost_by_security.get(holding.security_id, Decimal(0)) + cost_basis
        )

    total = sum(cost_by_security.values(), Decimal(0))
    if total > 0:
        weights = np.array(
            [
                float(cost_by_security.get(sid, Decimal(0)) / total)
                for sid in order_ids
            ],
            dtype=np.float64,
        )
        user_return, user_vol = portfolio_point(weights, mu, sigma)
    else:
        user_return = None
        user_vol = None

    # Optimal point at the user's gamma (if they have a risk profile).
    profile = await get_risk_profile(db, user_id)
    if profile is not None:
        w_opt = optimal_weights(
            np.asarray(mu, dtype=np.float64),
            np.asarray(sigma, dtype=np.float64),
            float(profile.crra_gamma),
        )
        opt_return, opt_vol = portfolio_point(w_opt, mu, sigma)
        gamma: Decimal | None = profile.crra_gamma
    else:
        opt_return = None
        opt_vol = None
        gamma = None

    return FrontierAnalysis(
        frontier=frontier,
        user_return=user_return,
        user_volatility=user_vol,
        optimal_return=opt_return,
        optimal_volatility=opt_vol,
        crra_gamma=gamma,
    )
