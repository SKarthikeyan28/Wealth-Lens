"""Pure command-parsing tests — the command -> API mapping, no DB or network."""

from __future__ import annotations

from decimal import Decimal

import pytest

from backend.telegram.commands import (
    CommandError,
    parse_command,
    parse_expense_args,
)


def test_parse_command_basic() -> None:
    cmd = parse_command("/summary")
    assert cmd.name == "summary"
    assert cmd.args == []


def test_parse_command_strips_botname_suffix() -> None:
    # Group chats deliver commands as /summary@MyBot.
    assert parse_command("/summary@WealthLensBot").name == "summary"


def test_parse_command_with_args() -> None:
    cmd = parse_command("/add_expense 12.50 food lunch with team")
    assert cmd.name == "add_expense"
    assert cmd.args == ["12.50", "food", "lunch", "with", "team"]


def test_parse_command_non_command_is_unknown() -> None:
    assert parse_command("hello there").name == "unknown"


def test_parse_expense_args_full() -> None:
    data = parse_expense_args(["12.50", "food", "lunch", "with", "team"])
    assert data.amount == Decimal("12.50")
    assert data.category == "food"
    assert data.note == "lunch with team"
    assert data.currency == "SGD"


def test_parse_expense_args_defaults_category() -> None:
    data = parse_expense_args(["9.00"])
    assert data.category == "uncategorised"
    assert data.note is None


def test_parse_expense_args_rejects_non_numeric_amount() -> None:
    with pytest.raises(CommandError):
        parse_expense_args(["abc", "food"])


def test_parse_expense_args_rejects_empty() -> None:
    with pytest.raises(CommandError):
        parse_expense_args([])


def test_parse_expense_args_rejects_negative_amount() -> None:
    with pytest.raises(CommandError):
        parse_expense_args(["-5", "food"])
