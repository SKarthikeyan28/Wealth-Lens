import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.errors import AppError
from backend.market.analytics import (
    FloatArray,
    annualize_covariance,
    annualize_log_return,
    covariance_matrix,
    log_returns,
)
from backend.market.models import AssetClass, FxRate, PriceHistory, Security
from backend.market.prices import DbPriceProvider


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


async def investable_universe(db: AsyncSession, start: date, end: date) -> list[Security]:
    """Securities with at least two price points in [start, end] — i.e. enough to
    estimate a return/covariance. Ordered by ticker for determinism."""
    counts = (
        select(PriceHistory.security_id)
        .where(PriceHistory.price_date >= start, PriceHistory.price_date <= end)
        .group_by(PriceHistory.security_id)
        .having(func.count() >= 2)
    )
    rows = await db.scalars(
        select(Security).where(Security.id.in_(counts)).order_by(Security.ticker)
    )
    return list(rows)


async def expected_returns_and_covariance(
    db: AsyncSession, security_ids: Sequence[uuid.UUID], start: date, end: date
) -> tuple[tuple[uuid.UUID, ...], FloatArray, FloatArray]:
    """Annualised expected-returns vector mu and covariance Sigma over the given
    securities, from aligned daily LOG returns. Returns the security-id order the
    columns correspond to (matrix column j == security_ids order from alignment),
    so callers can map weights back to securities. Raises AppError
    'INSUFFICIENT_PRICE_HISTORY' (422) if fewer than 2 aligned observations."""
    pm = await DbPriceProvider(db).close_prices(security_ids, start, end)
    if pm.prices.shape[0] < 2:
        raise AppError(
            "INSUFFICIENT_PRICE_HISTORY",
            "Need at least two aligned price observations to estimate returns.",
            422,
        )
    logret = log_returns(pm.prices)  # (T-1, N)
    mu = annualize_log_return(np.asarray(logret.mean(axis=0), dtype=np.float64))  # (N,)
    sigma = annualize_covariance(covariance_matrix(logret))  # (N, N)
    return pm.security_ids, mu, sigma
