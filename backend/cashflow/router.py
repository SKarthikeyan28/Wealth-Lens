import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.models import User
from backend.cashflow.schemas import (
    ExpenseCreate,
    ExpenseResponse,
    ExpenseUpdate,
    IncomeCreate,
    IncomeResponse,
    IncomeUpdate,
)
from backend.cashflow.service import (
    create_expense,
    create_income,
    delete_expense,
    delete_income,
    get_expense,
    get_income,
    list_expenses,
    list_income,
    update_expense,
    update_income,
)
from backend.common.database import get_db

income_router = APIRouter(prefix="/income", tags=["income"])
expense_router = APIRouter(prefix="/expenses", tags=["expenses"])


# --- Income ---

@income_router.post("", response_model=IncomeResponse, status_code=201)
async def create_income_route(
    payload: IncomeCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IncomeResponse:
    income = await create_income(db, user.id, payload)
    return IncomeResponse.model_validate(income)


@income_router.get("", response_model=list[IncomeResponse])
async def list_income_route(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[IncomeResponse]:
    rows = await list_income(db, user.id)
    return [IncomeResponse.model_validate(r) for r in rows]


@income_router.get("/{income_id}", response_model=IncomeResponse)
async def get_income_route(
    income_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IncomeResponse:
    income = await get_income(db, user.id, income_id)
    return IncomeResponse.model_validate(income)


@income_router.patch("/{income_id}", response_model=IncomeResponse)
async def update_income_route(
    income_id: uuid.UUID,
    payload: IncomeUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IncomeResponse:
    income = await update_income(db, user.id, income_id, payload)
    return IncomeResponse.model_validate(income)


@income_router.delete("/{income_id}", status_code=204)
async def delete_income_route(
    income_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_income(db, user.id, income_id)


# --- Expense ---

@expense_router.post("", response_model=ExpenseResponse, status_code=201)
async def create_expense_route(
    payload: ExpenseCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExpenseResponse:
    expense = await create_expense(db, user.id, payload)
    return ExpenseResponse.model_validate(expense)


@expense_router.get("", response_model=list[ExpenseResponse])
async def list_expenses_route(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ExpenseResponse]:
    rows = await list_expenses(db, user.id)
    return [ExpenseResponse.model_validate(r) for r in rows]


@expense_router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense_route(
    expense_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExpenseResponse:
    expense = await get_expense(db, user.id, expense_id)
    return ExpenseResponse.model_validate(expense)


@expense_router.patch("/{expense_id}", response_model=ExpenseResponse)
async def update_expense_route(
    expense_id: uuid.UUID,
    payload: ExpenseUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ExpenseResponse:
    expense = await update_expense(db, user.id, expense_id, payload)
    return ExpenseResponse.model_validate(expense)


@expense_router.delete("/{expense_id}", status_code=204)
async def delete_expense_route(
    expense_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_expense(db, user.id, expense_id)
