import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.accounts.models import Account, AccountType, Holding
from backend.auth.models import User
from backend.dashboard.service import allocation, net_worth
from backend.market.models import AssetClass, FxRate, Security


@pytest.mark.asyncio
async def test_net_worth_and_allocation_multicurrency(db_session: AsyncSession) -> None:
    db = db_session
    user_id = uuid.uuid4()
    acct_sgd = uuid.uuid4()
    acct_usd = uuid.uuid4()
    sec_id = uuid.uuid4()
    ticker = f"NW{uuid.uuid4().hex[:6].upper()}"

    db.add(User(id=user_id, email=f"nw-{uuid.uuid4().hex}@example.com", password_hash="x"))
    await db.flush()
    db.add(Account(id=acct_sgd, user_id=user_id, name="Cash SGD",
                   account_type=AccountType.CASH, currency="SGD", cash_balance=Decimal("1000.00")))
    db.add(Account(
        id=acct_usd, user_id=user_id, name="Brokerage USD",
        account_type=AccountType.BROKERAGE, currency="USD", cash_balance=Decimal("500.00"),
    ))
    db.add(Security(id=sec_id, ticker=ticker, name="World ETF",
                    asset_class=AssetClass.ETF, exchange="LSE", currency="USD"))
    # USD->SGD = 1.34 as of 2026-03-01
    await db.execute(
        delete(FxRate).where(FxRate.base_currency == "USD", FxRate.quote_currency == "SGD")
    )
    db.add(FxRate(id=uuid.uuid4(), base_currency="USD", quote_currency="SGD",
                  rate=Decimal("1.34"), as_of=date(2026, 3, 1)))
    await db.flush()
    db.add(Holding(id=uuid.uuid4(), account_id=acct_usd, security_id=sec_id,
                   quantity=Decimal("10"), avg_cost=Decimal("100.00")))
    await db.commit()

    on = date(2026, 3, 10)
    # 1000 SGD + (500 USD * 1.34 = 670) + (10*100=1000 USD * 1.34 = 1340) = 3010.00
    assert await net_worth(db, user_id, "SGD", on) == Decimal("3010.00")

    total, slices = await allocation(db, user_id, "SGD", on)
    assert total == Decimal("3010.00")
    by_class = {a: v for a, v, _ in slices}
    assert by_class["CASH"] == Decimal("1670.00")
    assert by_class["ETF"] == Decimal("1340.00")

    await db.execute(delete(Account).where(Account.user_id == user_id))  # cascades holdings
    await db.execute(delete(Security).where(Security.id == sec_id))
    await db.execute(
        delete(FxRate).where(FxRate.base_currency == "USD", FxRate.quote_currency == "SGD")
    )
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
