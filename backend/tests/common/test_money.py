from decimal import Decimal

from backend.common.money import minor_units, round_money


def test_banker_rounding_rounds_half_to_even() -> None:
    # .5 goes to the nearest EVEN digit — not always up (that would bias high).
    assert round_money(Decimal("2.345")) == Decimal("2.34")  # 4 is even -> down
    assert round_money(Decimal("2.355")) == Decimal("2.36")  # 6 is even -> up
    assert round_money(Decimal("0.125")) == Decimal("0.12")
    assert round_money(Decimal("0.135")) == Decimal("0.14")


def test_default_two_minor_units() -> None:
    assert minor_units("SGD") == 2
    assert round_money(Decimal("100")) == Decimal("100.00")


def test_zero_minor_unit_currency() -> None:
    assert minor_units("JPY") == 0
    assert round_money(Decimal("2.5"), "JPY") == Decimal("2")  # half-even -> 2
    assert round_money(Decimal("3.5"), "JPY") == Decimal("4")  # half-even -> 4


def test_currency_is_case_insensitive() -> None:
    assert minor_units("jpy") == 0
