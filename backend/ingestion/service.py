import csv
import hashlib
import io
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cashflow.models import Expense
from backend.common.errors import AppError
from backend.ingestion.models import ImportReceipt

_REQUIRED_COLUMNS = {"date", "amount", "category"}
_SOURCE = "expenses_csv"


@dataclass
class _ParsedExpense:
    spent_on: date
    amount: Decimal
    currency: str
    category: str
    note: str | None
    dedupe_hash: str


def _fingerprint(spent_on: date, amount: Decimal, currency: str, category: str, note: str) -> str:
    raw = f"{spent_on.isoformat()}|{amount}|{currency}|{category}|{note}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _decode(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")  # utf-8-sig transparently strips a BOM
    except UnicodeDecodeError:
        raise AppError("INVALID_ENCODING", "File must be UTF-8 encoded.", 400)


def parse_expense_rows(content: bytes) -> tuple[list[_ParsedExpense], list[dict[str, object]]]:
    reader = csv.DictReader(io.StringIO(_decode(content)))
    headers = {h.strip().lower() for h in (reader.fieldnames or [])}
    missing = _REQUIRED_COLUMNS - headers
    if missing:
        # Wrong columns is a whole-file problem — reject before importing anything.
        raise AppError(
            "INVALID_CSV_COLUMNS",
            f"Missing required columns: {', '.join(sorted(missing))}.",
            400,
        )

    parsed: list[_ParsedExpense] = []
    errors: list[dict[str, object]] = []
    # Row numbering starts at 2 (row 1 is the header), matching what a user sees.
    for i, raw in enumerate(reader, start=2):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        try:
            spent_on = date.fromisoformat(row["date"])
        except ValueError:
            errors.append({"row": i, "error": f"invalid date: {row.get('date', '')!r}"})
            continue
        try:
            amount = Decimal(row["amount"]).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            errors.append({"row": i, "error": f"invalid amount: {row.get('amount', '')!r}"})
            continue
        if amount < 0:
            errors.append({"row": i, "error": "amount must be >= 0"})
            continue
        category = row["category"]
        if not category:
            errors.append({"row": i, "error": "category is required"})
            continue
        currency = (row.get("currency") or "SGD").upper()
        if len(currency) != 3:
            errors.append({"row": i, "error": f"invalid currency: {currency!r}"})
            continue
        note = row.get("note") or None
        parsed.append(
            _ParsedExpense(
                spent_on=spent_on,
                amount=amount,
                currency=currency,
                category=category,
                note=note,
                dedupe_hash=_fingerprint(spent_on, amount, currency, category, note or ""),
            )
        )
    return parsed, errors


async def import_expenses_csv(
    db: AsyncSession, user_id: uuid.UUID, filename: str, content: bytes
) -> ImportReceipt:
    parsed, errors = parse_expense_rows(content)
    total_rows = len(parsed) + len(errors)

    # In-file dedup: identical rows within the SAME file collapse to one.
    unique: dict[str, _ParsedExpense] = {}
    for p in parsed:
        unique.setdefault(p.dedupe_hash, p)

    inserted = 0
    if unique:
        # ON CONFLICT DO NOTHING makes re-uploads idempotent; RETURNING counts
        # only the rows actually inserted (conflicts are excluded).
        stmt = (
            pg_insert(Expense)
            .values(
                [
                    {
                        "user_id": user_id,
                        "category": p.category,
                        "amount": p.amount,
                        "currency": p.currency,
                        "spent_on": p.spent_on,
                        "note": p.note,
                        "dedupe_hash": p.dedupe_hash,
                    }
                    for p in unique.values()
                ]
            )
            .on_conflict_do_nothing(index_elements=["user_id", "dedupe_hash"])
            .returning(Expense.id)
        )
        result = await db.scalars(stmt)
        inserted = len(list(result))

    receipt = ImportReceipt(
        id=uuid.uuid4(),
        user_id=user_id,
        source=_SOURCE,
        filename=filename,
        total_rows=total_rows,
        inserted=inserted,
        skipped_duplicates=len(parsed) - inserted,  # in-file dupes + already-in-db
        failed=len(errors),
        errors=errors,
    )
    db.add(receipt)
    await db.commit()  # valid expenses + receipt land together
    return receipt


async def get_import_receipt(
    db: AsyncSession, user_id: uuid.UUID, receipt_id: uuid.UUID
) -> ImportReceipt:
    receipt = await db.scalar(
        select(ImportReceipt).where(
            ImportReceipt.id == receipt_id, ImportReceipt.user_id == user_id
        )
    )
    if receipt is None:
        raise AppError("RECEIPT_NOT_FOUND", "Import receipt not found.", 404)
    return receipt
