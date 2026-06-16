"""Lazy Redis client singleton — the infra seam for caching, mirroring the
async engine setup in common.database. Redis is an optimisation layer, so callers
must degrade gracefully when it is unavailable (see market.covcache)."""

from __future__ import annotations

import os

from redis.asyncio import Redis

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        _redis = Redis.from_url(url, decode_responses=True)
    return _redis
