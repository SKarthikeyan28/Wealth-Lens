import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cashflow.models import Expense, Income, IncomeSource
from backend.cashflow.schemas import (
    ExpenseCreate,
    ExpenseUpdate,
    IncomeCreate,
    IncomeUpdate,
)
from backend.common.audit import write_audit
from backend.common.errors import AppError


def _income_snapshot(i: Income) -> dict[str, object]:
    st = i.source_type
    return {
        "id": str(i.id),
        "user_id": str(i.user_id),
        "source_type": st.value if isinstance(st, IncomeSource) else st,
        "amount": str(i.amount),
        "currency": i.currency,
        "received_on": i.received_on.isoformat(),
        "note": i.note,
    }


def _expense_snapshot(e: Expense) -> dict[str, object]:
    return {
        "id": str(e.id),
        "user_id": str(e.user_id),
        "category": e.category,
        "amount": str(e.amount),
        "currency": e.currency,
        "spent_on": e.spent_on.isoformat(),
        "note": e.note,
    }


# --- Income ---

async def _get_owned_income(db: AsyncSession, user_id: uuid.UUID, income_id: uuid.UUID) -> Income:
    obj = await db.scalar(
        select(Income).where(Income.id == income_id, Income.user_id == user_id)
    )
    if obj is None:
        raise AppError("INCOME_NOT_FOUND", "Income entry not found.", 404)
    return obj


async def list_income(db: AsyncSession, user_id: uuid.UUID) -> list[Income]:
    rows = await db.scalars(
        select(Income).where(Income.user_id == user_id).order_by(Income.received_on)
    )
    return list(rows)


async def get_income(db: AsyncSession, user_id: uuid.UUID, income_id: uuid.UUID) -> Income:
    return await _get_owned_income(db, user_id, income_id)


async def create_income(db: AsyncSession, user_id: uuid.UUID, data: IncomeCreate) -> Income:
    income = Income(
        id=uuid.uuid4(),
        user_id=user_id,
        source_type=data.source_type,
        amount=data.amount,
        currency=data.currency,
        received_on=data.received_on,
        note=data.note,
    )
    db.add(income)
    await write_audit(
        db,
        actor_id=user_id,
        action="CREATE",
        entity_type="income",
        entity_id=income.id,
        new_data=_income_snapshot(income),
    )
    await db.commit()
    return income


async def update_income(
    db: AsyncSession, user_id: uuid.UUID, income_id: uuid.UUID, data: IncomeUpdate
) -> Income:
    income = await _get_owned_income(db, user_id, income_id)
    old = _income_snapshot(income)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(income, field, value)
    await write_audit(
        db,
        actor_id=user_id,
        action="UPDATE",
        entity_type="income",
        entity_id=income.id,
        old_data=old,
        new_data=_income_snapshot(income),
    )
    await db.commit()
    return income


async def delete_income(db: AsyncSession, user_id: uuid.UUID, income_id: uuid.UUID) -> None:
    income = await _get_owned_income(db, user_id, income_id)
    old = _income_snapshot(income)
    await db.delete(income)
    await write_audit(
        db,
        actor_id=user_id,
        action="DELETE",
        entity_type="income",
        entity_id=income_id,
        old_data=old,
    )
    await db.commit()


# --- Expense ---

async def _get_owned_expense(
    db: AsyncSession, user_id: uuid.UUID, expense_id: uuid.UUID
) -> Expense:
    obj = await db.scalar(
        select(Expense).where(Expense.id == expense_id, Expense.user_id == user_id)
    )
    if obj is None:
        raise AppError("EXPENSE_NOT_FOUND", "Expense entry not found.", 404)
    return obj


async def list_expenses(db: AsyncSession, user_id: uuid.UUID) -> list[Expense]:
    rows = await db.scalars(
        select(Expense).where(Expense.user_id == user_id).order_by(Expense.spent_on)
    )
    return list(rows)


async def get_expense(db: AsyncSession, user_id: uuid.UUID, expense_id: uuid.UUID) -> Expense:
    return await _get_owned_expense(db, user_id, expense_id)


async def create_expense(db: AsyncSession, user_id: uuid.UUID, data: ExpenseCreate) -> Expense:
    expense = Expense(
        id=uuid.uuid4(),
        user_id=user_id,
        category=data.category,
        amount=data.amount,
        currency=data.currency,
        spent_on=data.spent_on,
        note=data.note,
    )
    db.add(expense)
    await write_audit(
        db,
        actor_id=user_id,
        action="CREATE",
        entity_type="expense",
        entity_id=expense.id,
        new_data=_expense_snapshot(expense),
    )
    await db.commit()
    return expense


async def update_expense(
    db: AsyncSession, user_id: uuid.UUID, expense_id: uuid.UUID, data: ExpenseUpdate
) -> Expense:
    expense = await _get_owned_expense(db, user_id, expense_id)
    old = _expense_snapshot(expense)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(expense, field, value)
    await write_audit(
        db,
        actor_id=user_id,
        action="UPDATE",
        entity_type="expense",
        entity_id=expense.id,
        old_data=old,
        new_data=_expense_snapshot(expense),
    )
    await db.commit()
    return expense


async def delete_expense(db: AsyncSession, user_id: uuid.UUID, expense_id: uuid.UUID) -> None:
    expense = await _get_owned_expense(db, user_id, expense_id)
    old = _expense_snapshot(expense)
    await db.delete(expense)
    await write_audit(
        db,
        actor_id=user_id,
        action="DELETE",
        entity_type="expense",
        entity_id=expense_id,
        old_data=old,
    )
    await db.commit()
