"""Redis-backed cache for covariance matrices — a decorator over a PriceProvider.

Key:  cov:v1:g{generation}:{ids_fingerprint}:{start}:{end}:{annualized}
Invalidation: bump a single generation counter (INCR), making every existing key
unreachable in O(1); orphans expire via TTL. The cache is best-effort — if Redis
is unavailable we degrade to computing directly from the provider.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Sequence
from datetime import date

import numpy as np
from redis.asyncio import Redis
from redis.exceptions import RedisError

from backend.market.analytics import FloatArray
from backend.market.prices import PriceProvider, covariance_from_prices

COV_SCHEMA = "v1"
COV_TTL_SECONDS = 3600
_GEN_KEY = "market:prices:gen"


def _ids_fingerprint(security_ids: Sequence[uuid.UUID]) -> str:
    """Order-sensitive fingerprint — column order is part of the result."""
    joined = "|".join(str(s) for s in security_ids)
    return hashlib.sha256(joined.encode()).hexdigest()[:16]


def covariance_key(
    generation: int,
    security_ids: Sequence[uuid.UUID],
    start: date,
    end: date,
    annualized: bool,
) -> str:
    return (
        f"cov:{COV_SCHEMA}:g{generation}:{_ids_fingerprint(security_ids)}"
        f":{start.isoformat()}:{end.isoformat()}:{int(annualized)}"
    )


async def covariance_cached(
    redis: Redis,
    provider: PriceProvider,
    security_ids: Sequence[uuid.UUID],
    start: date,
    end: date,
    *,
    annualized: bool = True,
) -> FloatArray:
    """Return the cached covariance matrix, computing and caching it on a miss.
    Degrades to a direct compute if Redis is unavailable."""
    try:
        generation = int(await redis.get(_GEN_KEY) or 0)
        key = covariance_key(generation, security_ids, start, end, annualized)
        hit = await redis.get(key)
        if hit is not None:
            return np.asarray(json.loads(hit), dtype=np.float64)
    except RedisError:
        pm = await provider.close_prices(security_ids, start, end)
        return covariance_from_prices(pm, annualized=annualized)

    pm = await provider.close_prices(security_ids, start, end)
    cov = covariance_from_prices(pm, annualized=annualized)
    try:
        await redis.set(key, json.dumps(cov.tolist()), ex=COV_TTL_SECONDS)
    except RedisError:
        pass  # best-effort write; never fail the request on a cache write
    return cov


async def invalidate_price_cache(redis: Redis) -> None:
    """Call after any price_history write. Bumps the generation counter so all
    existing covariance keys become unreachable (orphans expire via TTL)."""
    await redis.incr(_GEN_KEY)
