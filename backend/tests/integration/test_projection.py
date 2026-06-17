import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.models import User
from backend.crra.models import RiskProfile
from backend.crra.service import optimal_allocation
from backend.market.models import AssetClass, PriceHistory, Security
from backend.montecarlo.service import project_goal


@pytest.mark.asyncio
async def test_project_goal_assumptions_bands_and_reproducibility(
    db_session: AsyncSession,
) -> None:
    db = db_session

    user_id = uuid.uuid4()
    db.add(User(id=user_id, email=f"proj-{uuid.uuid4().hex}@example.com", password_hash="x"))

    risky_id, safe_id = uuid.uuid4(), uuid.uuid4()
    risky_tick = f"RISKY{uuid.uuid4().hex[:5].upper()}"
    safe_tick = f"SAFE{uuid.uuid4().hex[:5].upper()}"
    db.add(Security(id=risky_id, ticker=risky_tick, name="Risky",
                    asset_class=AssetClass.EQUITY, exchange="LSE", currency="USD"))
    db.add(Security(id=safe_id, ticker=safe_tick, name="Safe",
                    asset_class=AssetClass.BOND, exchange="LSE", currency="USD"))
    await db.flush()

    # ~6 aligned daily prices inside the optimal_allocation 5y default window.
    days = [date.today().replace(month=1, day=d) for d in (2, 5, 6, 7, 8, 9)]
    risky_prices = [
        Decimal("100.00"),
        Decimal("104.00"),
        Decimal("99.00"),
        Decimal("103.00"),
        Decimal("98.50"),
        Decimal("100.80"),
    ]
    safe_prices = [
        Decimal("50.00"),
        Decimal("50.05"),
        Decimal("50.10"),
        Decimal("50.16"),
        Decimal("50.21"),
        Decimal("50.27"),
    ]
    for d, p in zip(days, risky_prices):
        db.add(PriceHistory(id=uuid.uuid4(), security_id=risky_id, price_date=d, close_price=p))
    for d, p in zip(days, safe_prices):
        db.add(PriceHistory(id=uuid.uuid4(), security_id=safe_id, price_date=d, close_price=p))

    db.add(RiskProfile(
        id=uuid.uuid4(),
        user_id=user_id,
        crra_gamma=Decimal("3.000"),
        crra_gamma_low=Decimal("2.000"),
        crra_gamma_high=Decimal("3.500"),
    ))
    await db.commit()

    result = await project_goal(
        db, user_id, goal_amount=200000, years=10, initial_wealth=100000,
        annual_contribution=10000, n_sims=5000, seed=1,
    )

    # Probability is a valid empirical probability.
    assert 0.0 <= result.probability <= 1.0

    # One band per year 0..years.
    assert len(result.bands) == 11

    # Percentiles are ordered at the final year.
    final = result.bands[-1]
    assert final.p10 <= final.p50 <= final.p90

    # Assumptions echoed = the optimal allocation's mean/volatility.
    end = date.today()
    start = end.replace(year=end.year - 5)
    alloc = await optimal_allocation(db, user_id, start=start, end=end)
    assert result.mean_return == pytest.approx(alloc.expected_return)
    assert result.volatility == pytest.approx(alloc.volatility)

    # Echoed knobs.
    assert result.n_sims == 5000
    assert result.seed == 1

    # Reproducibility: same seed -> identical probability.
    result2 = await project_goal(
        db, user_id, goal_amount=200000, years=10, initial_wealth=100000,
        annual_contribution=10000, n_sims=5000, seed=1,
    )
    assert result2.probability == result.probability

    await db.execute(delete(RiskProfile).where(RiskProfile.user_id == user_id))
    await db.execute(delete(Security).where(Security.id.in_([risky_id, safe_id])))
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
