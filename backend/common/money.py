from decimal import ROUND_HALF_EVEN, Decimal

# Minor units (decimal places) per ISO 4217. Default is 2; a few are 0.
_MINOR_UNITS: dict[str, int] = {
    "JPY": 0,
    "KRW": 0,
}


def minor_units(currency: str) -> int:
    return _MINOR_UNITS.get(currency.upper(), 2)


def round_money(value: Decimal, currency: str = "SGD") -> Decimal:
    """Round a monetary Decimal to the currency's minor units using banker's
    rounding (ROUND_HALF_EVEN).

    PRESENTATION LAYER ONLY. Never call this inside intermediate calculations —
    carry full precision through the math and round once, at the end, for display.
    Rounding mid-calculation compounds error across steps.
    """
    exponent = Decimal(1).scaleb(-minor_units(currency))  # 2 -> 0.01, 0 -> 1
    return value.quantize(exponent, rounding=ROUND_HALF_EVEN)
