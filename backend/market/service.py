import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.errors import AppError
from backend.market.models import AssetClass, FxRate, Security


async def get_or_create_security(
    db: AsyncSession,
    *,
    ticker: str,
    exchange: str | None,
    asset_class: AssetClass,
    currency: str,
    name: str | None = None,
) -> Security:
    stmt = select(Security).where(Security.ticker == ticker)
    # NULL exchange needs IS NULL, not = NULL (which matches nothing in SQL).
    stmt = (
        stmt.where(Security.exchange.is_(None))
        if exchange is None
        else stmt.where(Security.exchange == exchange)
    )
    existing = await db.scalar(stmt)
    if existing is not None:
        return existing

    security = Security(
        id=uuid.uuid4(),
        ticker=ticker,
        exchange=exchange,
        asset_class=asset_class,
        currency=currency,
        name=name,
    )
    db.add(security)
    # No commit: the caller owns the transaction so the whole multi-step
    # write (security + holding + audit) stays atomic.
    return security


async def convert_as_of(
    db: AsyncSession,
    amount: Decimal,
    from_currency: str,
    to_currency: str,
    as_of: date,
) -> Decimal:
    """Convert `amount` using the FX rate effective on or before `as_of` (the most
    recent such rate). Returns full Decimal precision — round at presentation only.
    """
    f, t = from_currency.upper(), to_currency.upper()
    if f == t:
        return amount

    # Direct rate: 1 f = rate t, the most recent rate dated on/before as_of.
    rate = await db.scalar(
        select(FxRate.rate)
        .where(FxRate.base_currency == f, FxRate.quote_currency == t, FxRate.as_of <= as_of)
        .order_by(FxRate.as_of.desc())
        .limit(1)
    )
    if rate is not None:
        return amount * rate

    # Inverse fallback: only t->f is seeded, so 1 f = 1/rate t.
    inverse = await db.scalar(
        select(FxRate.rate)
        .where(FxRate.base_currency == t, FxRate.quote_currency == f, FxRate.as_of <= as_of)
        .order_by(FxRate.as_of.desc())
        .limit(1)
    )
    if inverse is not None:
        return amount / inverse

    raise AppError(
        "FX_RATE_NOT_FOUND",
        f"No FX rate for {f}->{t} as of {as_of.isoformat()}.",
        422,
    )
