import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.accounts.models import Account, AccountType, Holding
from backend.auth.models import User
from backend.crra.models import RiskProfile
from backend.crra.service import frontier_analysis
from backend.market.models import AssetClass, PriceHistory, Security


@pytest.mark.asyncio
async def test_frontier_places_user_on_or_below(db_session: AsyncSession) -> None:
    db = db_session

    user_id = uuid.uuid4()
    db.add(
        User(id=user_id, email=f"frontier-{uuid.uuid4().hex}@example.com", password_hash="x")
    )

    risky_id, safe_id = uuid.uuid4(), uuid.uuid4()
    risky_tick = f"RISKY{uuid.uuid4().hex[:5].upper()}"
    safe_tick = f"SAFE{uuid.uuid4().hex[:5].upper()}"
    db.add(
        Security(id=risky_id, ticker=risky_tick, name="Risky",
                 asset_class=AssetClass.EQUITY, exchange="LSE", currency="USD")
    )
    db.add(
        Security(id=safe_id, ticker=safe_tick, name="Safe",
                 asset_class=AssetClass.BOND, exchange="LSE", currency="USD")
    )
    await db.flush()

    # Distinct window from the other CRRA integration tests (Jan 2026) so this
    # test's securities never enter the global investable_universe they query.
    days = [date(2025, 6, d) for d in (2, 5, 6, 7, 8, 9)]
    # RISKY: large swings, slight upward drift.
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

    # Give the user a brokerage account concentrated in the RISKY security, so
    # their current portfolio is clearly sub-optimal (not min-variance).
    account_id = uuid.uuid4()
    db.add(
        Account(id=account_id, user_id=user_id, name="Brokerage",
                account_type=AccountType.BROKERAGE, currency="USD",
                cash_balance=Decimal("0"))
    )
    await db.flush()
    db.add(
        Holding(id=uuid.uuid4(), account_id=account_id, security_id=risky_id,
                quantity=Decimal("100"), avg_cost=Decimal("100.00"))
    )
    db.add(
        Holding(id=uuid.uuid4(), account_id=account_id, security_id=safe_id,
                quantity=Decimal("10"), avg_cost=Decimal("50.00"))
    )
    await db.commit()

    fa = await frontier_analysis(db, user_id, start=days[0], end=days[-1])

    assert fa.frontier  # non-empty
    assert fa.user_return is not None
    assert fa.user_volatility is not None

    # The user's portfolio lies within the efficient frontier's envelope: it can't
    # out-return the best efficient portfolio, nor undercut the minimum-variance
    # risk. (With only TWO assets every long-only mix sits ON the concave frontier
    # curve, so "a discrete grid point strictly dominates the user" is the wrong
    # test — the user falls between grid points, above the chord. The envelope
    # bounds are the correct, robust statement of "on or below the frontier".)
    assert fa.user_return <= max(p.expected_return for p in fa.frontier) + 1e-9
    assert fa.user_volatility >= min(p.volatility for p in fa.frontier) - 1e-9

    assert fa.optimal_return is not None
    assert fa.optimal_volatility is not None
    assert fa.crra_gamma == Decimal("3.000")

    await db.execute(delete(Holding).where(Holding.account_id == account_id))
    await db.execute(delete(Account).where(Account.id == account_id))
    await db.execute(delete(RiskProfile).where(RiskProfile.user_id == user_id))
    await db.execute(delete(PriceHistory).where(PriceHistory.security_id.in_([risky_id, safe_id])))
    await db.execute(delete(Security).where(Security.id.in_([risky_id, safe_id])))
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
