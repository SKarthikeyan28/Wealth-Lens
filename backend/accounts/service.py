import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.accounts.models import Account, AccountType
from backend.accounts.schemas import AccountCreate, AccountUpdate
from backend.common.audit import write_audit
from backend.common.errors import AppError


def _snapshot(a: Account) -> dict[str, object]:
    at = a.account_type
    return {
        "id": str(a.id),
        "user_id": str(a.user_id),
        "name": a.name,
        "account_type": at.value if isinstance(at, AccountType) else at,
        "currency": a.currency,
        "cash_balance": str(a.cash_balance),
    }


async def _get_owned(db: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID) -> Account:
    account = await db.scalar(
        select(Account).where(Account.id == account_id, Account.user_id == user_id)
    )
    # 404 (not 403) whether it doesn't exist OR isn't yours — never leak existence.
    if account is None:
        raise AppError("ACCOUNT_NOT_FOUND", "Account not found.", 404)
    return account


async def list_accounts(db: AsyncSession, user_id: uuid.UUID) -> list[Account]:
    rows = await db.scalars(
        select(Account).where(Account.user_id == user_id).order_by(Account.created_at)
    )
    return list(rows)


async def get_account(db: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID) -> Account:
    return await _get_owned(db, user_id, account_id)


async def create_account(db: AsyncSession, user_id: uuid.UUID, data: AccountCreate) -> Account:
    account = Account(
        user_id=user_id,
        name=data.name,
        account_type=data.account_type,
        currency=data.currency,
        cash_balance=data.cash_balance,
    )
    db.add(account)
    await db.flush()            # INSERT runs inside the txn → account.id is now populated
    await db.refresh(account)   # load server defaults (created_at)
    await write_audit(
        db,
        actor_id=user_id,
        action="CREATE",
        entity_type="account",
        entity_id=account.id,
        new_data=_snapshot(account),
    )
    await db.commit()           # the ONE commit: account row + audit row land together
    return account


async def update_account(
    db: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID, data: AccountUpdate
) -> Account:
    account = await _get_owned(db, user_id, account_id)
    old = _snapshot(account)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(account, field, value)   # only fields the client actually sent (PATCH)
    await db.flush()
    await db.refresh(account)
    await write_audit(
        db,
        actor_id=user_id,
        action="UPDATE",
        entity_type="account",
        entity_id=account.id,
        old_data=old,
        new_data=_snapshot(account),
    )
    await db.commit()
    return account


async def delete_account(db: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID) -> None:
    account = await _get_owned(db, user_id, account_id)
    old = _snapshot(account)
    await db.delete(account)
    await write_audit(
        db,
        actor_id=user_id,
        action="DELETE",
        entity_type="account",
        entity_id=account_id,
        old_data=old,
    )
    await db.commit()
