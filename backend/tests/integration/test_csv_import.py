import uuid

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.models import User
from backend.cashflow.models import Expense
from backend.ingestion.models import ImportReceipt
from backend.ingestion.service import import_expenses_csv

_CSV = (
    b"date,amount,category,note\n"
    b"2026-06-01,10.00,Food,lunch\n"
    b"2026-06-02,20.00,Transport,\n"
)


async def _make_user(db: AsyncSession) -> uuid.UUID:
    user_id = uuid.uuid4()
    db.add(User(id=user_id, email=f"imp-{uuid.uuid4().hex}@example.com", password_hash="x"))
    await db.commit()
    return user_id


async def _cleanup(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(delete(Expense).where(Expense.user_id == user_id))
    await db.execute(delete(ImportReceipt).where(ImportReceipt.user_id == user_id))
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()


@pytest.mark.asyncio
async def test_csv_import_is_idempotent(db_session: AsyncSession) -> None:
    db = db_session
    user_id = await _make_user(db)

    first = await import_expenses_csv(db, user_id, "march.csv", _CSV)
    assert (first.inserted, first.skipped_duplicates, first.failed) == (2, 0, 0)

    # Same file again: idempotent — nothing new, both rows skipped as duplicates.
    second = await import_expenses_csv(db, user_id, "march.csv", _CSV)
    assert (second.inserted, second.skipped_duplicates, second.failed) == (0, 2, 0)

    count = await db.scalar(
        select(func.count()).select_from(Expense).where(Expense.user_id == user_id)
    )
    assert count == 2  # no duplicates created

    await _cleanup(db, user_id)


@pytest.mark.asyncio
async def test_csv_import_partial_failure(db_session: AsyncSession) -> None:
    db = db_session
    user_id = await _make_user(db)

    mixed = b"date,amount,category\n2026-06-01,10.00,Food\nbad,5,Food\n2026-06-03,7.00,Transport\n"
    receipt = await import_expenses_csv(db, user_id, "mixed.csv", mixed)
    assert receipt.inserted == 2  # two good rows imported
    assert receipt.failed == 1  # one bad row reported, not fatal

    count = await db.scalar(
        select(func.count()).select_from(Expense).where(Expense.user_id == user_id)
    )
    assert count == 2  # valid rows landed; the bad row caused zero corruption

    await _cleanup(db, user_id)
