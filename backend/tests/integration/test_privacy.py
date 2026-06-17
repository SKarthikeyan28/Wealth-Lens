"""Phase 5.5.2: account deletion (cascading + audit-preserving) and data export.

Proves the gate's hard part — deleting a user erases their financial data via FK
cascade, but the append-only audit log (no FK to users) survives, pseudonymised.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.accounts.models import Account, AccountType
from backend.auth.models import User
from backend.auth.security import hash_password
from backend.cashflow.models import Expense
from backend.cashflow.schemas import ExpenseCreate
from backend.cashflow.service import create_expense
from backend.common.audit import AuditLog
from backend.common.errors import AppError
from backend.privacy.service import delete_account, export_data

PASSWORD = "Str0ng!Passw0rd"


async def _seed_user(db: AsyncSession) -> User:
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"priv-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password(PASSWORD),
    )
    db.add(user)
    await db.flush()  # land the user row before the FK-dependent account insert
    db.add(
        Account(
            id=uuid.uuid4(),
            user_id=user_id,
            name="Cash",
            account_type=AccountType.CASH,
            currency="SGD",
            cash_balance=Decimal("100.00"),
        )
    )
    await db.commit()
    # An expense write produces an audit row (the trail we must preserve on delete).
    await create_expense(
        db,
        user_id,
        ExpenseCreate(
            category="food", amount=Decimal("9.00"), currency="SGD", spent_on=date.today()
        ),
    )
    return user


@pytest.mark.asyncio
async def test_export_includes_data_excludes_credentials(db_session: AsyncSession) -> None:
    db = db_session
    user = await _seed_user(db)
    try:
        data = await export_data(db, user)
        assert data["profile"]["email"] == user.email
        assert "password_hash" not in data["profile"]
        assert "totp_secret" not in str(data)
        assert len(data["accounts"]) == 1
        assert len(data["expenses"]) == 1
        assert len(data["audit_log"]) >= 1
    finally:
        await db.delete(user)  # cascade cleanup; audit rows persist by design
        await db.commit()


@pytest.mark.asyncio
async def test_delete_cascades_data_but_preserves_audit(db_session: AsyncSession) -> None:
    db = db_session
    user = await _seed_user(db)
    uid = user.id
    before = (
        await db.scalar(
            select(func.count()).select_from(AuditLog).where(AuditLog.actor_id == uid)
        )
    ) or 0

    await delete_account(db, user, PASSWORD)

    # User and financial data are gone (FK cascade)...
    assert await db.scalar(select(User).where(User.id == uid)) is None
    expense_count = (
        await db.scalar(
            select(func.count()).select_from(Expense).where(Expense.user_id == uid)
        )
    ) or 0
    assert expense_count == 0
    # ...but the audit trail survived, plus the new DELETE event.
    after = (
        await db.scalar(
            select(func.count()).select_from(AuditLog).where(AuditLog.actor_id == uid)
        )
    ) or 0
    assert after >= before + 1


@pytest.mark.asyncio
async def test_delete_wrong_password_rejected(db_session: AsyncSession) -> None:
    db = db_session
    user = await _seed_user(db)
    uid = user.id
    try:
        with pytest.raises(AppError) as exc:
            await delete_account(db, user, "wrong-password")
        assert exc.value.status_code == 401
        assert await db.scalar(select(User).where(User.id == uid)) is not None
    finally:
        await db.delete(user)
        await db.commit()
