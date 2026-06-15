import uuid
from datetime import date
from decimal import Decimal

import numpy as np

from backend.market.prices import align_close_prices


def test_alignment_keeps_only_common_dates() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    d1, d2, d3, d4 = (date(2026, 1, i) for i in (2, 5, 6, 7))
    rows = [
        (a, d1, Decimal("100.00")),
        (a, d2, Decimal("110.00")),
        (a, d3, Decimal("121.00")),
        (a, d4, Decimal("133.10")),
        (b, d1, Decimal("50.00")),
        (b, d2, Decimal("49.00")),
        # b has a GAP on d3 — that date must be dropped for both assets.
        (b, d4, Decimal("50.50")),
    ]
    pm = align_close_prices([a, b], rows)
    assert pm.dates == (d1, d2, d4)  # d3 dropped (intersection)
    assert pm.prices.shape == (3, 2)  # T=3 common dates, N=2 assets
    assert pm.prices.dtype == np.float64  # Decimal -> float at the boundary
    np.testing.assert_allclose(pm.prices[:, 0], [100.0, 110.0, 133.10])
    np.testing.assert_allclose(pm.prices[:, 1], [50.0, 49.0, 50.50])


def test_column_order_follows_requested_security_ids() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    d1 = date(2026, 1, 2)
    rows = [(a, d1, Decimal("1")), (b, d1, Decimal("2"))]
    # Request b first: column 0 must be b's price.
    pm = align_close_prices([b, a], rows)
    assert pm.security_ids == (b, a)
    np.testing.assert_allclose(pm.prices[0], [2.0, 1.0])


def test_empty_security_list_yields_empty_matrix() -> None:
    pm = align_close_prices([], [])
    assert pm.prices.shape == (0, 0)
