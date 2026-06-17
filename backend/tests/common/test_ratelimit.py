"""Fixed-window limiter: blocks past the limit, and FAILS OPEN if Redis is down."""

from __future__ import annotations

import pytest
from redis.exceptions import RedisError

from backend.common import ratelimit
from backend.common.errors import AppError


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    async def expire(self, key: str, seconds: int) -> bool:
        return True


class _BrokenRedis:
    async def incr(self, key: str) -> int:
        raise RedisError("down")

    async def expire(self, key: str, seconds: int) -> bool:
        return True


@pytest.mark.asyncio
async def test_allows_up_to_limit_then_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRedis()
    monkeypatch.setattr(ratelimit, "get_redis", lambda: fake)
    for _ in range(3):
        await ratelimit._hit("rl:test:ip", limit=3, window=60)  # within limit
    with pytest.raises(AppError) as exc:
        await ratelimit._hit("rl:test:ip", limit=3, window=60)  # 4th -> blocked
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_fails_open_when_redis_down(monkeypatch: pytest.MonkeyPatch) -> None:
    broken = _BrokenRedis()
    monkeypatch.setattr(ratelimit, "get_redis", lambda: broken)
    # Must not raise even past the limit — availability over a hard guarantee.
    await ratelimit._hit("rl:test:ip", limit=1, window=60)
    await ratelimit._hit("rl:test:ip", limit=1, window=60)


class _FakeClient:
    host = "1.2.3.4"


class _FakeRequest:
    client = _FakeClient()


@pytest.mark.asyncio
async def test_dependency_wiring_blocks_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    # Prove the FastAPI dependency keys on client IP and enforces via _hit.
    monkeypatch.setenv("RATELIMIT_ENABLED", "true")
    fake = _FakeRedis()
    monkeypatch.setattr(ratelimit, "get_redis", lambda: fake)
    dependency = ratelimit.rate_limit(limit=1, window=60, scope="wiring")
    await dependency(_FakeRequest())  # type: ignore[arg-type]
    with pytest.raises(AppError):
        await dependency(_FakeRequest())  # type: ignore[arg-type]
