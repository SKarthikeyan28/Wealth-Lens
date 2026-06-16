import uuid
from collections.abc import Sequence
from datetime import date

import numpy as np
import pytest

from backend.common.cache import get_redis
from backend.market.covcache import covariance_cached, invalidate_price_cache
from backend.market.prices import PriceMatrix


class StubProvider:
    """Counts calls so we can prove a cache hit avoids recomputation."""

    def __init__(self, cov_seed: float) -> None:
        self.calls = 0
        self._seed = cov_seed

    async def close_prices(
        self, security_ids: Sequence[uuid.UUID], start: date, end: date
    ) -> PriceMatrix:
        self.calls += 1
        # Two observations -> covariance is computable and deterministic.
        prices = np.array([[100.0, 50.0], [100.0 + self._seed, 50.5]])
        return PriceMatrix(tuple(security_ids), (start, end), prices)


@pytest.mark.asyncio
async def test_hit_miss_and_invalidation() -> None:
    redis = get_redis()
    ids = [uuid.uuid4(), uuid.uuid4()]
    start, end = date(2026, 1, 2), date(2026, 1, 3)
    provider = StubProvider(cov_seed=1.0)

    first = await covariance_cached(redis, provider, ids, start, end)
    assert provider.calls == 1  # miss -> computed
    second = await covariance_cached(redis, provider, ids, start, end)
    assert provider.calls == 1  # hit -> not recomputed
    np.testing.assert_allclose(first, second)

    await invalidate_price_cache(redis)
    await covariance_cached(redis, provider, ids, start, end)
    assert provider.calls == 2  # generation bumped -> recomputed
