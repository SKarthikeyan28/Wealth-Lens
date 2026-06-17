"""CRRA gamma elicitation: the fixed "risk ladder" that infers risk aversion.

Pure functions — no DB, no I/O, no cvxpy. Reuses the verified engine
(`certainty_equivalent`); this module only sequences questions and scores
answers.

A user cannot state their CRRA gamma directly, so we infer it from choices. We
present a FIXED, NON-ADAPTIVE ladder (a "multiple price list" / staircase): a
series of questions, each offering the SAME 50/50 gamble (win GAMBLE_HIGH vs win
GAMBLE_LOW) against a guaranteed amount C. Each C is the certainty equivalent of
that gamble at a known gamma "cut point". Because the CE decreases as gamma
rises, the guaranteed amounts DESCEND down the ladder, and a rational responder
switches from preferring the sure amount to preferring the gamble exactly at
their own gamma — so the count of "sure" answers brackets their gamma.

Why fixed rather than an adaptive binary search? The indifference math is
identical, but a fixed list is stateless and free of question-order effects (an
adaptive staircase can be gamed or anchored by the path taken). The trade-off is
coarser resolution, which we report honestly: the recovered gamma is a BAND, and
the band MIDPOINT is the point estimate handed to the optimiser (4.3c).

Float boundary: like `engine.py`, these are utility-space projections over an
assumed gamble, not ledger money, so everything stays float64 — Decimal would
buy false precision.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from backend.crra.engine import certainty_equivalent

GAMBLE_HIGH = 200.0
GAMBLE_LOW = 100.0
# Ascending gamma cut points -> 6 risk bands. Sure amounts (CE at each cut point)
# DESCEND, so a rational responder's "sure" answers count up to their gamma band.
GAMMA_CUT_POINTS: tuple[float, ...] = (0.5, 1.0, 2.0, 3.5, 6.0)
GAMMA_FLOOR = 0.0  # lower edge of the most aggressive band
GAMMA_CAP = 10.0  # upper edge of the most conservative (open-ended) band


@dataclass(frozen=True)
class LadderQuestion:
    gamble_high: float
    gamble_low: float
    sure_amount: float  # = certainty_equivalent([HIGH, LOW], [0.5, 0.5], gamma_cut)
    gamma_cut: float


@dataclass(frozen=True)
class GammaEstimate:
    gamma_low: float
    gamma_high: float
    gamma_point: float  # midpoint of [gamma_low, gamma_high]


def sure_amount(gamma_cut: float) -> float:
    """The guaranteed amount that makes a responder with aversion gamma_cut
    exactly indifferent to the 50/50 gamble: its certainty equivalent."""
    return certainty_equivalent([GAMBLE_HIGH, GAMBLE_LOW], [0.5, 0.5], gamma_cut)


def ladder() -> list[LadderQuestion]:
    """The full risk ladder: one question per cut point, in GAMMA_CUT_POINTS
    order, with its sure amount filled in. Sure amounts descend down the list."""
    return [
        LadderQuestion(
            gamble_high=GAMBLE_HIGH,
            gamble_low=GAMBLE_LOW,
            sure_amount=sure_amount(gamma_cut),
            gamma_cut=gamma_cut,
        )
        for gamma_cut in GAMMA_CUT_POINTS
    ]


def estimate_gamma(answers: Sequence[bool]) -> GammaEstimate:
    """Score a completed ladder into a gamma BAND plus its midpoint.

    `answers[i] is True` means the user chose the SURE amount on question i
    (preferred the guaranteed C over the gamble). More "sure" answers => more
    risk-averse => higher gamma.

    Scoring assumes a MONOTONE responder: as the sure amounts descend, once a
    rational person prefers the gamble they prefer it for every lower amount too,
    so the answers are a run of True followed by a run of False. We therefore use
    the standard multiple-price-list score, `k = number of True answers`, and do
    not penalise non-monotone (inconsistent) patterns here — k still locates the
    switch point.

    With edges = (GAMMA_FLOOR,) + GAMMA_CUT_POINTS + (GAMMA_CAP,), k indexes the
    band: k=0 -> (FLOOR, cut[0]); k=len(cuts) -> (cut[-1], CAP); else
    (cut[k-1], cut[k]). The point estimate is the band midpoint.
    """
    if len(answers) != len(GAMMA_CUT_POINTS):
        raise ValueError(
            f"answers must have length {len(GAMMA_CUT_POINTS)}, got {len(answers)}"
        )
    edges = (GAMMA_FLOOR, *GAMMA_CUT_POINTS, GAMMA_CAP)
    k = sum(1 for a in answers if a)
    gamma_low = edges[k]
    gamma_high = edges[k + 1]
    gamma_point = (gamma_low + gamma_high) / 2
    return GammaEstimate(gamma_low=gamma_low, gamma_high=gamma_high, gamma_point=gamma_point)


def rational_answers(true_gamma: float) -> list[bool]:
    """Simulate a perfectly rational responder with risk aversion true_gamma:
    they take the sure amount on a question whenever it meets or beats their own
    certainty equivalent for the gamble. Useful for tests and for round-tripping
    the estimator."""
    own_ce = certainty_equivalent([GAMBLE_HIGH, GAMBLE_LOW], [0.5, 0.5], true_gamma)
    return [sure_amount(gamma_cut) >= own_ce for gamma_cut in GAMMA_CUT_POINTS]
