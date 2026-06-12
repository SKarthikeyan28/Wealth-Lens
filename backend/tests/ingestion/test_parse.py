from decimal import Decimal

import pytest

from backend.common.errors import AppError
from backend.ingestion.service import parse_expense_rows


def test_missing_required_columns_rejects_whole_file() -> None:
    content = b"date,amount\n2026-06-01,10\n"  # no 'category'
    with pytest.raises(AppError) as exc:
        parse_expense_rows(content)
    assert exc.value.code == "INVALID_CSV_COLUMNS"


def test_valid_row_parses() -> None:
    content = b"date,amount,category,note\n2026-06-01,10.50,Food,lunch\n"
    parsed, errors = parse_expense_rows(content)
    assert errors == []
    assert len(parsed) == 1
    assert parsed[0].amount == Decimal("10.50")
    assert parsed[0].category == "Food"


def test_bad_rows_reported_not_raised() -> None:
    content = b"date,amount,category\n2026-06-01,10,Food\nnotadate,5,Food\n2026-06-02,-3,Food\n"
    parsed, errors = parse_expense_rows(content)
    assert len(parsed) == 1  # only the first row is valid
    assert [e["row"] for e in errors] == [3, 4]  # bad date, negative amount


def test_identical_rows_share_a_fingerprint() -> None:
    content = b"date,amount,category\n2026-06-01,10,Food\n2026-06-01,10,Food\n"
    parsed, _ = parse_expense_rows(content)
    assert parsed[0].dedupe_hash == parsed[1].dedupe_hash


def test_bom_is_handled() -> None:
    # Leading "﻿" is a UTF-8 BOM; utf-8-sig decoding must strip it so the
    # first header is "date", not "﻿date".
    content = ("﻿" + "date,amount,category\n2026-06-01,10,Food\n").encode("utf-8")
    parsed, errors = parse_expense_rows(content)
    assert errors == []
    assert len(parsed) == 1
