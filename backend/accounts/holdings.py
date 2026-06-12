import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.accounts.models import Account, Holding
from backend.accounts.schemas import HoldingCreate
from backend.common.audit import write_audit
from backend.common.errors import AppError
from backend.market.service import get_or_create_security


def _holding_snapshot(h: Holding) -> dict[str, object]:
    return {
        "id": str(h.id),
        "account_id": str(h.account_id),
        "security_id": str(h.security_id),
        "quantity": str(h.quantity),
        "avg_cost": str(h.avg_cost),
    }


async def _get_owned_account(
    db: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID
) -> Account:
    account = await db.scalar(
        select(Account).where(Account.id == account_id, Account.user_id == user_id)
    )
    if account is None:
        raise AppError("ACCOUNT_NOT_FOUND", "Account not found.", 404)
    return account


async def create_holding(db: AsyncSession, user_id: uuid.UUID, data: HoldingCreate) -> Holding:
    # ONE transaction, multiple steps:
    #   (1) verify account ownership
    #   (2) find-or-create the shared security (market interface; does NOT commit)
    #   (3) insert the holding
    #   (4) write the audit row
    #   (5) commit once — all or nothing
    await _get_owned_account(db, user_id, data.account_id)
    security = await get_or_create_security(
        db,
        ticker=data.ticker,
        exchange=data.exchange,
        asset_class=data.asset_class,
        currency=data.currency,
        name=data.name,
    )
    # Flush so a newly-created security is INSERTed before the holding that FKs to
    # it. There is no relationship() between Holding and Security (only a bare FK
    # column), so the unit-of-work won't order these inserts itself. This stays in
    # the same transaction — still one commit, atomicity intact.
    await db.flush()
    holding = Holding(
        id=uuid.uuid4(),
        account_id=data.account_id,
        security_id=security.id,
        quantity=data.quantity,
        avg_cost=data.avg_cost,
    )
    db.add(holding)
    await write_audit(
        db,
        actor_id=user_id,
        action="CREATE",
        entity_type="holding",
        entity_id=holding.id,
        new_data=_holding_snapshot(holding),
    )
    try:
        await db.commit()
    except IntegrityError:
        # Duplicate (account_id, security_id) hits the UNIQUE constraint at commit.
        # The rollback discards the staged security + holding + audit together.
        await db.rollback()
        raise AppError("HOLDING_EXISTS", "This account already holds this security.", 409)
    return holding


async def list_holdings(
    db: AsyncSession, user_id: uuid.UUID, account_id: uuid.UUID
) -> list[Holding]:
    await _get_owned_account(db, user_id, account_id)
    rows = await db.scalars(
        select(Holding).where(Holding.account_id == account_id).order_by(Holding.created_at)
    )
    return list(rows)


async def delete_holding(db: AsyncSession, user_id: uuid.UUID, holding_id: uuid.UUID) -> None:
    # Ownership enforced via join: the holding's account must belong to the user.
    holding = await db.scalar(
        select(Holding)
        .join(Account, Holding.account_id == Account.id)
        .where(Holding.id == holding_id, Account.user_id == user_id)
    )
    if holding is None:
        raise AppError("HOLDING_NOT_FOUND", "Holding not found.", 404)
    old = _holding_snapshot(holding)
    await db.delete(holding)
    await write_audit(
        db,
        actor_id=user_id,
        action="DELETE",
        entity_type="holding",
        entity_id=holding_id,
        old_data=old,
    )
    await db.commit()
