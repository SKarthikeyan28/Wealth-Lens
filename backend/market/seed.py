"""Committed static price dataset — the 'known prices' the engine is built and
verified against before any live API is wired in (Phase 4 de-risking rule).

Idempotent: re-running inserts only securities/prices that don't already exist.
Run with:  python -m backend.market.seed
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.market.models import AssetClass, PriceHistory, Security

# (ticker, exchange, name, asset_class, currency)
SEED_SECURITIES: list[tuple[str, str, str, AssetClass, str]] = [
    ("VWRA", "LSE", "Vanguard FTSE All-World", AssetClass.ETF, "USD"),
    ("AGGU", "LSE", "iShares Global Aggregate Bond", AssetClass.BOND, "USD"),
]

# Adjusted close prices, keyed by ticker. Deliberately short and committed so the
# numbers are reviewable; these are simulated, not real market data.
SEED_PRICES: dict[str, list[tuple[date, Decimal]]] = {
    "VWRA": [
        (date(2026, 1, 2), Decimal("100.00")),
        (date(2026, 1, 5), Decimal("101.50")),
        (date(2026, 1, 6), Decimal("100.80")),
        (date(2026, 1, 7), Decimal("102.30")),
        (date(2026, 1, 8), Decimal("103.10")),
    ],
    "AGGU": [
        (date(2026, 1, 2), Decimal("50.00")),
        (date(2026, 1, 5), Decimal("49.90")),
        (date(2026, 1, 6), Decimal("50.05")),
        (date(2026, 1, 7), Decimal("49.95")),
        (date(2026, 1, 8), Decimal("50.10")),
    ],
}


async def seed_market_data(db: AsyncSession) -> None:
    """Idempotently insert the seed securities and their price history."""
    ticker_to_id: dict[str, uuid.UUID] = {}
    for ticker, exchange, name, asset_class, currency in SEED_SECURITIES:
        existing = await db.scalar(
            select(Security).where(
                Security.ticker == ticker, Security.exchange == exchange
            )
        )
        if existing is None:
            existing = Security(
                id=uuid.uuid4(),
                ticker=ticker,
                name=name,
                asset_class=asset_class,
                exchange=exchange,
                currency=currency,
            )
            db.add(existing)
            await db.flush()
        ticker_to_id[ticker] = existing.id

    for ticker, points in SEED_PRICES.items():
        security_id = ticker_to_id[ticker]
        for price_date, close in points:
            seen = await db.scalar(
                select(PriceHistory).where(
                    PriceHistory.security_id == security_id,
                    PriceHistory.price_date == price_date,
                )
            )
            if seen is None:
                db.add(
                    PriceHistory(
                        id=uuid.uuid4(),
                        security_id=security_id,
                        price_date=price_date,
                        close_price=close,
                    )
                )
    await db.commit()


async def _main() -> None:
    # Mirrors the session setup in common.database.get_db for a one-off script.
    from backend.common.database import _get_session_factory

    async with _get_session_factory()() as db:
        await seed_market_data(db)


if __name__ == "__main__":
    asyncio.run(_main())
