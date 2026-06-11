import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.market.models import AssetClass, Security


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
