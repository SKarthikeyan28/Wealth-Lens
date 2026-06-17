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


@pytest.mark.asyncio
async def test_optimal_allocation_favours_low_variance(db_session: AsyncSession) -> None:
    db = db_session

    user_id = uuid.uuid4()
    db.add(User(id=user_id, email=f"alloc-{uuid.uuid4().hex}@example.com", password_hash="x"))

    risky_id, safe_id = uuid.uuid4(), uuid.uuid4()
    risky_tick = f"RISKY{uuid.uuid4().hex[:5].upper()}"
    safe_tick = f"SAFE{uuid.uuid4().hex[:5].upper()}"
    db.add(Security(id=risky_id, ticker=risky_tick, name="Risky",
                    asset_class=AssetClass.EQUITY, exchange="LSE", currency="USD"))
    db.add(Security(id=safe_id, ticker=safe_tick, name="Safe",
                    asset_class=AssetClass.BOND, exchange="LSE", currency="USD"))
    await db.flush()

    # Unique window (no other test or prior run uses 2024-03) so the GLOBAL
    # investable universe in this window holds only this test's two securities —
    # robust to the persistent test DB and to other tests' leftovers.
    days = [date(2024, 3, d) for d in (2, 5, 6, 7, 8, 9)]
    # RISKY: large swings each day, only a slight upward drift over the window.
    risky_prices = [
        Decimal("100.00"),
        Decimal("104.00"),
        Decimal("99.00"),
        Decimal("103.00"),
        Decimal("98.50"),
        Decimal("100.80"),
    ]
    # SAFE: barely moves, slight upward drift.
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

    rp = RiskProfile(
        id=uuid.uuid4(),
        user_id=user_id,
        crra_gamma=Decimal("3.000"),
        crra_gamma_low=Decimal("2.000"),
        crra_gamma_high=Decimal("3.500"),
    )
    db.add(rp)
    await db.commit()

    result = await optimal_allocation(db, user_id, start=days[0], end=days[-1])

    # Exactly two slices; weights sum to ~1; long-only (no negatives); tickers present.
    assert len(result.slices) == 2
    weights = {s.ticker: s.weight for s in result.slices}
    assert risky_tick in weights and safe_tick in weights
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-6)
    assert all(s.weight >= -1e-9 for s in result.slices)

    # Risk aversion favours the low-variance asset.
    safe_w_g3 = weights[safe_tick]
    assert safe_w_g3 > weights[risky_tick]

    # Monotone toward safety: a much higher gamma => >= weight on SAFE.
    rp.crra_gamma = Decimal("20.000")
    rp.crra_gamma_low = Decimal("18.000")
    rp.crra_gamma_high = Decimal("22.000")
    await db.commit()

    result_high = await optimal_allocation(db, user_id, start=days[0], end=days[-1])
    safe_w_g20 = {s.ticker: s.weight for s in result_high.slices}[safe_tick]
    assert safe_w_g20 >= safe_w_g3 - 1e-9

    await db.execute(delete(RiskProfile).where(RiskProfile.user_id == user_id))
    await db.execute(delete(Security).where(Security.id.in_([risky_id, safe_id])))
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
