import json
import uuid
from datetime import date

import numpy as np

from backend.market.covcache import _ids_fingerprint, covariance_key


def test_key_is_deterministic_and_order_sensitive() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    start, end = date(2026, 1, 2), date(2026, 1, 8)
    k1 = covariance_key(0, [a, b], start, end, True)
    assert k1 == covariance_key(0, [a, b], start, end, True)  # deterministic
    assert k1 != covariance_key(0, [b, a], start, end, True)  # column order matters
    assert k1.startswith("cov:v1:g0:")


def test_generation_bump_changes_the_key() -> None:
    a = uuid.uuid4()
    args = ([a], date(2026, 1, 2), date(2026, 1, 8), True)
    assert covariance_key(0, *args) != covariance_key(1, *args)


def test_fingerprint_differs_by_membership() -> None:
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    assert _ids_fingerprint([a, b]) != _ids_fingerprint([a, c])


def test_covariance_json_roundtrip_preserves_values() -> None:
    cov = np.array([[0.04, 0.01], [0.01, 0.09]])
    restored = np.asarray(json.loads(json.dumps(cov.tolist())), dtype=np.float64)
    np.testing.assert_allclose(restored, cov)
