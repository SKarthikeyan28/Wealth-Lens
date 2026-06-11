import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.accounts.schemas import AccountCreate, AccountResponse, AccountUpdate
from backend.accounts.service import (
    create_account,
    delete_account,
    get_account,
    list_accounts,
    update_account,
)
from backend.auth.dependencies import get_current_user
from backend.auth.models import User
from backend.common.database import get_db

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("", response_model=AccountResponse, status_code=201)
async def create(
    payload: AccountCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AccountResponse:
    account = await create_account(db, user.id, payload)
    return AccountResponse.model_validate(account)


@router.get("", response_model=list[AccountResponse])
async def list_all(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AccountResponse]:
    accounts = await list_accounts(db, user.id)
    return [AccountResponse.model_validate(a) for a in accounts]


@router.get("/{account_id}", response_model=AccountResponse)
async def get_one(
    account_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AccountResponse:
    account = await get_account(db, user.id, account_id)
    return AccountResponse.model_validate(account)


@router.patch("/{account_id}", response_model=AccountResponse)
async def update(
    account_id: uuid.UUID,
    payload: AccountUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AccountResponse:
    account = await update_account(db, user.id, account_id, payload)
    return AccountResponse.model_validate(account)


@router.delete("/{account_id}", status_code=204)
async def delete(
    account_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_account(db, user.id, account_id)
