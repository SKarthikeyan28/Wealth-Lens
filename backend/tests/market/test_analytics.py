import numpy as np

from backend.market import analytics


def test_simple_returns_from_prices() -> None:
    prices = np.array([100.0, 110.0, 121.0])
    np.testing.assert_allclose(analytics.simple_returns(prices), [0.10, 0.10])


def test_log_returns_are_time_additive() -> None:
    prices = np.array([100.0, 110.0, 121.0])
    lr = analytics.log_returns(prices)
    np.testing.assert_allclose(lr, [np.log(1.1), np.log(1.1)])
    # Sum of two daily log returns == single log return over the whole span.
    assert np.isclose(lr.sum(), np.log(121.0 / 100.0))


def test_covariance_matrix_hand_checked() -> None:
    # rows = time observations, cols = assets (A, B)
    returns = np.array(
        [
            [0.10, 0.05],
            [0.20, 0.15],
            [0.30, 0.10],
        ]
    )
    cov = analytics.covariance_matrix(returns)  # ddof=1
    expected = np.array(
        [
            [0.01, 0.0025],
            [0.0025, 0.0025],
        ]
    )
    np.testing.assert_allclose(cov, expected)


def test_correlation_matrix_hand_checked() -> None:
    returns = np.array([[0.10, 0.05], [0.20, 0.15], [0.30, 0.10]])
    corr = analytics.correlation_matrix(returns)
    np.testing.assert_allclose(corr, [[1.0, 0.5], [0.5, 1.0]])


def test_annualize_covariance_scales_linearly() -> None:
    cov = np.array([[0.0004]])
    np.testing.assert_allclose(analytics.annualize_covariance(cov), [[0.0004 * 252]])
