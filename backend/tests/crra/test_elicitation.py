import pytest

from backend.crra.elicitation import (
    GAMMA_CUT_POINTS,
    estimate_gamma,
    ladder,
    rational_answers,
    sure_amount,
)


def test_sure_amount_log_utility_is_geometric_mean() -> None:
    # gamma=1 -> geometric mean = sqrt(200*100) ~= 141.4214
    assert sure_amount(1.0) == pytest.approx(141.4214, abs=1e-3)


def test_sure_amount_gamma_two_worked() -> None:
    # gamma=2 -> CE = 400/3 ~= 133.3333
    assert sure_amount(2.0) == pytest.approx(133.3333, abs=1e-3)


def test_ladder_sure_amounts_strictly_decreasing() -> None:
    amounts = [q.sure_amount for q in ladder()]
    for lo, hi in zip(amounts[1:], amounts[:-1]):
        assert lo < hi


def test_ladder_shape_and_cut_points() -> None:
    questions = ladder()
    assert len(questions) == 5
    for question, cut in zip(questions, GAMMA_CUT_POINTS):
        assert question.gamma_cut == cut
        assert question.gamble_high == 200.0
        assert question.gamble_low == 100.0


def test_estimate_gamma_band_mapping() -> None:
    cases = [
        (0, 0.0, 0.5, 0.25),
        (1, 0.5, 1.0, 0.75),
        (2, 1.0, 2.0, 1.5),
        (3, 2.0, 3.5, 2.75),
        (4, 3.5, 6.0, 4.75),
        (5, 6.0, 10.0, 8.0),
    ]
    for n_true, expected_low, expected_high, expected_point in cases:
        answers = [True] * n_true + [False] * (5 - n_true)
        est = estimate_gamma(answers)
        assert est.gamma_low == pytest.approx(expected_low)
        assert est.gamma_high == pytest.approx(expected_high)
        assert est.gamma_point == pytest.approx(expected_point)


def test_round_trip_brackets_true_gamma() -> None:
    for true_gamma in [0.3, 0.75, 1.5, 2.5, 4.0, 7.0]:
        est = estimate_gamma(rational_answers(true_gamma))
        assert est.gamma_low <= true_gamma <= est.gamma_high


def test_estimate_gamma_rejects_wrong_length() -> None:
    with pytest.raises(ValueError):
        estimate_gamma([True, False, True])


def test_estimate_gamma_point_is_positive() -> None:
    for n_true in range(6):
        answers = [True] * n_true + [False] * (5 - n_true)
        assert estimate_gamma(answers).gamma_point > 0
