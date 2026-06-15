import uuid
from datetime import date
from decimal import Decimal

import numpy as np
import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.market.models import AssetClass, PriceHistory, Security
from backend.market.prices import DbPriceProvider, covariance_from_prices


@pytest.mark.asyncio
async def test_seed_load_align_covariance(db_session: AsyncSession) -> None:
    db = db_session
    sec_a, sec_b = uuid.uuid4(), uuid.uuid4()
    tick_a = f"CVA{uuid.uuid4().hex[:6].upper()}"
    tick_b = f"CVB{uuid.uuid4().hex[:6].upper()}"
    db.add(Security(id=sec_a, ticker=tick_a, name="A",
                    asset_class=AssetClass.ETF, exchange="LSE", currency="USD"))
    db.add(Security(id=sec_b, ticker=tick_b, name="B",
                    asset_class=AssetClass.BOND, exchange="LSE", currency="USD"))
    await db.flush()

    days = [date(2026, 1, d) for d in (2, 5, 6, 7)]
    a_prices = [Decimal("100"), Decimal("110"), Decimal("121"), Decimal("133.10")]
    b_prices = [Decimal("50"), Decimal("49"), Decimal("50"), Decimal("50.50")]
    for d, pa in zip(days, a_prices):
        db.add(PriceHistory(id=uuid.uuid4(), security_id=sec_a, price_date=d, close_price=pa))
    # sec_b is missing day index 2 — alignment must drop it for both.
    for d, pb in zip([days[0], days[1], days[3]], [b_prices[0], b_prices[1], b_prices[3]]):
        db.add(PriceHistory(id=uuid.uuid4(), security_id=sec_b, price_date=d, close_price=pb))
    await db.commit()

    pm = await DbPriceProvider(db).close_prices([sec_a, sec_b], days[0], days[-1])
    assert pm.dates == (days[0], days[1], days[3])  # gap day dropped
    assert pm.prices.shape == (3, 2)

    cov = covariance_from_prices(pm)  # annualised log-return covariance
    assert cov.shape == (2, 2)
    assert cov[0, 0] > 0 and cov[1, 1] > 0  # positive variances
    np.testing.assert_allclose(cov, cov.T)  # covariance is symmetric

    await db.execute(delete(Security).where(Security.id.in_([sec_a, sec_b])))  # cascades prices
    await db.commit()
