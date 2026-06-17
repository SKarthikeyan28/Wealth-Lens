import logging
import os
from collections.abc import Awaitable, Callable

from fastapi import Request
from redis.exceptions import RedisError

from backend.common.cache import get_redis
from backend.common.errors import AppError

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    # Operational kill-switch (default on); disabled in the test env for isolation.
    return os.environ.get("RATELIMIT_ENABLED", "true").lower() == "true"


async def _hit(key: str, limit: int, window: int) -> None:
    redis = get_redis()
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window)
    except (RedisError, RuntimeError, OSError):
        # Fail open: the limiter is best-effort — a Redis blip (RedisError/OSError),
        # or an event-loop edge in the async client (RuntimeError), must never break
        # the request path or lock users out. Log and allow.
        logger.warning("rate limiter unavailable; allowing request", extra={"key": key})
        return
    if count > limit:
        raise AppError("RATE_LIMITED", "Too many requests. Please slow down.", 429)


def rate_limit(limit: int, window: int, scope: str) -> Callable[[Request], Awaitable[None]]:
    """FastAPI dependency factory: fixed-window per-client-IP limiter. Fixed window
    is simple and atomic (INCR+EXPIRE) but allows up to ~2x `limit` across a window
    boundary — acceptable here; a sliding window would remove that at more cost."""

    async def dependency(request: Request) -> None:
        if not _enabled():
            return
        # Direct peer IP. Behind a proxy, trust X-Forwarded-For only from a known
        # proxy (Phase 6 deployment concern), not from the raw header.
        client_ip = request.client.host if request.client else "unknown"
        await _hit(f"rl:{scope}:{client_ip}", limit, window)

    return dependency
