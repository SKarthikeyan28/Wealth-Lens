import uuid
from decimal import Decimal

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.accounts.holdings import create_holding
from backend.accounts.models import Account, AccountType, Holding
from backend.accounts.schemas import HoldingCreate
from backend.auth.models import User
from backend.common.audit import AuditLog
from backend.common.errors import AppError
from backend.market.models import AssetClass, Security


@pytest.mark.asyncio
async def test_duplicate_holding_rolls_back_fully(db_session: AsyncSession) -> None:
    db = db_session

    # Plain-UUID identifiers held in Python vars — never read back off an ORM
    # instance, so a post-rollback lazy-load can't trip the async session.
    user_id = uuid.uuid4()
    account_id = uuid.uuid4()
    ticker = f"TST{uuid.uuid4().hex[:8].upper()}"

    db.add(User(id=user_id, email=f"hold-{uuid.uuid4().hex}@example.com", password_hash="x"))
    # Flush the user before adding the account: there is no relationship() between
    # them, only a bare user_id FK column, so the unit-of-work won't auto-order the
    # inserts. Flushing here guarantees the user row exists before the account FK.
    await db.flush()
    db.add(
        Account(
            id=account_id,
            user_id=user_id,
            name="Brokerage",
            account_type=AccountType.BROKERAGE,
            currency="USD",
        )
    )
    await db.commit()

    data = HoldingCreate(
        account_id=account_id,
        ticker=ticker,
        exchange="LSE",
        asset_class=AssetClass.ETF,
        currency="USD",
        quantity=Decimal("10"),
        avg_cost=Decimal("100"),
    )

    async def counts() -> tuple[int, int, int]:
        secs = await db.scalar(
            select(func.count()).select_from(Security).where(Security.ticker == ticker)
        )
        holds = await db.scalar(
            select(func.count()).select_from(Holding).where(Holding.account_id == account_id)
        )
        audits = await db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.actor_id == user_id, AuditLog.entity_type == "holding")
        )
        return secs or 0, holds or 0, audits or 0

    # First add: security + holding + audit all land together.
    await create_holding(db, user_id, data)
    assert await counts() == (1, 1, 1)

    # Second add of the same security violates UNIQUE(account_id, security_id).
    with pytest.raises(AppError) as exc:
        await create_holding(db, user_id, data)
    assert exc.value.code == "HOLDING_EXISTS"

    # The failed write rolled back FULLY: no second holding, and no audit row for
    # the mutation that never committed. Counts are unchanged. Atomicity proven.
    assert await counts() == (1, 1, 1)

    # Clean up via SQL DELETE on captured UUIDs (no ORM attribute access).
    # CASCADE removes the holding. Audit rows are immutable + uniquely scoped, so left.
    await db.execute(delete(Account).where(Account.id == account_id))
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
