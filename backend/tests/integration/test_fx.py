import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.market.models import FxRate
from backend.market.service import convert_as_of


@pytest.mark.asyncio
async def test_fx_uses_rate_as_of_valuation_date(db_session: AsyncSession) -> None:
    db = db_session
    # Clean any residue from a prior run (fx_rates is shared reference data).
    await db.execute(delete(FxRate).where(FxRate.base_currency.in_(["USD", "SGD"])))
    db.add(FxRate(id=uuid.uuid4(), base_currency="USD", quote_currency="SGD",
                  rate=Decimal("1.35"), as_of=date(2026, 1, 1)))
    db.add(FxRate(id=uuid.uuid4(), base_currency="USD", quote_currency="SGD",
                  rate=Decimal("1.34"), as_of=date(2026, 3, 1)))
    await db.commit()

    # As of Feb 15: the Jan-1 rate is the most recent on/before that date.
    feb = await convert_as_of(db, Decimal("100"), "USD", "SGD", date(2026, 2, 15))
    assert feb == Decimal("135.00")
    # As of Mar 10: the Mar-1 rate now applies.
    mar = await convert_as_of(db, Decimal("100"), "USD", "SGD", date(2026, 3, 10))
    assert mar == Decimal("134.00")
    # Inverse direction uses 1/rate.
    inverse = await convert_as_of(db, Decimal("134"), "SGD", "USD", date(2026, 3, 10))
    assert inverse == Decimal("100")
    # Same currency is identity.
    same = await convert_as_of(db, Decimal("50"), "SGD", "SGD", date(2026, 3, 10))
    assert same == Decimal("50")

    await db.execute(delete(FxRate).where(FxRate.base_currency.in_(["USD", "SGD"])))
    await db.commit()
