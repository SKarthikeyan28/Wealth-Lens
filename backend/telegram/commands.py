from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError

from backend.cashflow.schemas import ExpenseCreate


class CommandError(Exception):
    """A user-facing problem with the command text (bad amount, missing args)."""


@dataclass(frozen=True)
class ParsedCommand:
    name: str
    args: list[str]


def parse_command(text: str) -> ParsedCommand:
    text = text.strip()
    if not text.startswith("/"):
        return ParsedCommand("unknown", [])
    parts = text.split()
    name = parts[0][1:].split("@", 1)[0].lower()  # strip /cmd@BotName suffix
    return ParsedCommand(name, parts[1:])


def parse_expense_args(args: list[str]) -> ExpenseCreate:
    """`/add_expense <amount> [category] [note...]` -> ExpenseCreate (SGD, today).
    Reuses the REST schema so validation rules stay in one place."""
    if not args:
        raise CommandError("Usage: /add_expense <amount> [category] [note]")
    try:
        amount = Decimal(args[0])
    except InvalidOperation:
        raise CommandError("Amount must be a number, e.g. 12.50")
    category = args[1] if len(args) > 1 else "uncategorised"
    note = " ".join(args[2:]) or None
    try:
        return ExpenseCreate(
            category=category, amount=amount, currency="SGD", spent_on=date.today(), note=note
        )
    except ValidationError:
        raise CommandError("Invalid expense — amount must be >= 0 and category 1-80 chars.")
