"""Price loading and alignment: the bridge from stored Decimal prices to the
float64 returns matrix the analytics engine consumes.

Swappable provider: `PriceProvider` is the interface; `DbPriceProvider` reads
seeded `price_history`. A live-API provider (4.1d) satisfies the same Protocol,
so the math is built and verified against static data first.

Corporate actions: this loader's contract is that it consumes ADJUSTED close
prices. A split/dividend back-adjusts the historical series at the source (the
"adjusted close"); a raw 2:1 split would otherwise look like a -50% return. Our
static seed stores already-adjusted prices; the live provider requests adjusted
series. The math layer below only ever sees a clean, adjusted series.

The Decimal -> float64 boundary lives here: prices are stored as NUMERIC/Decimal
and converted to float64 while building the matrix (see `align_close_prices`).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.common.errors import AppError
from backend.market import analytics
from backend.market.analytics import FloatArray
from backend.market.models import PriceHistory


@dataclass(frozen=True)
class PriceMatrix:
    """Aligned close prices for N securities over T common dates.

    `prices[t, j]` is the adjusted close of `security_ids[j]` on `dates[t]`.
    Column order follows `security_ids`; only dates on which EVERY security has a
    price are included (inner join) — a missing observation is never fabricated.
    """

    security_ids: tuple[uuid.UUID, ...]
    dates: tuple[date, ...]
    prices: FloatArray  # shape (T, N), float64


class PriceProvider(Protocol):
    """Swappable source of historical adjusted close prices."""

    async def close_prices(
        self, security_ids: Sequence[uuid.UUID], start: date, end: date
    ) -> PriceMatrix: ...


def align_close_prices(
    security_ids: Sequence[uuid.UUID],
    rows: Iterable[tuple[uuid.UUID, date, Decimal]],
) -> PriceMatrix:
    """Align raw (security_id, date, price) rows into a dense (T, N) matrix.

    Pure function — no I/O, so it's directly unit-testable. Keeps only dates
    common to every requested security (inner join) and converts Decimal prices
    to float64 here, at the analytics boundary.
    """
    by_sec: dict[uuid.UUID, dict[date, Decimal]] = {sid: {} for sid in security_ids}
    for sid, d, price in rows:
        if sid in by_sec:
            by_sec[sid][d] = price

    if not security_ids:
        return PriceMatrix((), (), np.empty((0, 0), dtype=np.float64))

    common = set(by_sec[security_ids[0]].keys())
    for sid in security_ids[1:]:
        common &= set(by_sec[sid].keys())
    ordered = sorted(common)

    t, n = len(ordered), len(security_ids)
    matrix = np.empty((t, n), dtype=np.float64)
    for i, d in enumerate(ordered):
        for j, sid in enumerate(security_ids):
            matrix[i, j] = float(by_sec[sid][d])

    return PriceMatrix(tuple(security_ids), tuple(ordered), matrix)


class DbPriceProvider:
    """Reads adjusted close prices from the seeded `price_history` table."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def close_prices(
        self, security_ids: Sequence[uuid.UUID], start: date, end: date
    ) -> PriceMatrix:
        if not security_ids:
            return PriceMatrix((), (), np.empty((0, 0), dtype=np.float64))
        result = await self._db.execute(
            select(
                PriceHistory.security_id,
                PriceHistory.price_date,
                PriceHistory.close_price,
            )
            .where(
                PriceHistory.security_id.in_(security_ids),
                PriceHistory.price_date >= start,
                PriceHistory.price_date <= end,
            )
            .order_by(PriceHistory.price_date)
        )
        rows = [(r[0], r[1], r[2]) for r in result.all()]
        return align_close_prices(security_ids, rows)


def covariance_from_prices(pm: PriceMatrix, *, annualized: bool = True) -> FloatArray:
    """Annualised (by default) log-return covariance matrix for an aligned
    PriceMatrix. Requires at least two aligned observations."""
    if pm.prices.shape[0] < 2:
        raise AppError(
            "INSUFFICIENT_PRICE_HISTORY",
            "Need at least two aligned price observations to estimate covariance.",
            422,
        )
    cov = analytics.covariance_matrix(analytics.log_returns(pm.prices))
    return analytics.annualize_covariance(cov) if annualized else cov
