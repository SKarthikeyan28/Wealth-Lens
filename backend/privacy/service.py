from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.accounts.models import Account, Holding
from backend.auth.models import User
from backend.auth.security import verify_password
from backend.cashflow.models import Expense, Goal, Income
from backend.common.audit import AuditLog, write_audit
from backend.common.errors import AppError
from backend.crra.models import RiskProfile
from backend.telegram.models import TelegramLink


async def export_data(db: AsyncSession, user: User) -> dict[str, Any]:
    """Subject-access export: every record we hold for this user, EXCLUDING their
    own credentials (password hash, TOTP secret are never exported)."""
    uid = user.id
    accounts = list(await db.scalars(select(Account).where(Account.user_id == uid)))
    account_ids = [a.id for a in accounts]
    holdings = (
        list(await db.scalars(select(Holding).where(Holding.account_id.in_(account_ids))))
        if account_ids
        else []
    )
    income = list(await db.scalars(select(Income).where(Income.user_id == uid)))
    expenses = list(await db.scalars(select(Expense).where(Expense.user_id == uid)))
    goals = list(await db.scalars(select(Goal).where(Goal.user_id == uid)))
    profile = await db.scalar(select(RiskProfile).where(RiskProfile.user_id == uid))
    tg = await db.scalar(select(TelegramLink).where(TelegramLink.user_id == uid))
    audit = list(
        await db.scalars(
            select(AuditLog).where(AuditLog.actor_id == uid).order_by(AuditLog.created_at)
        )
    )

    return {
        "profile": {
            "id": str(user.id),
            "email": user.email,
            "created_at": user.created_at.isoformat(),
            "totp_enabled": user.totp_enabled,
        },
        "accounts": [
            {
                "id": str(a.id),
                "name": a.name,
                "account_type": a.account_type.value,
                "currency": a.currency,
                "cash_balance": str(a.cash_balance),
                "created_at": a.created_at.isoformat(),
            }
            for a in accounts
        ],
        "holdings": [
            {
                "id": str(h.id),
                "account_id": str(h.account_id),
                "security_id": str(h.security_id),
                "quantity": str(h.quantity),
                "avg_cost": str(h.avg_cost),
            }
            for h in holdings
        ],
        "income": [
            {
                "id": str(i.id),
                "source_type": i.source_type.value,
                "amount": str(i.amount),
                "currency": i.currency,
                "received_on": i.received_on.isoformat(),
                "note": i.note,
            }
            for i in income
        ],
        "expenses": [
            {
                "id": str(e.id),
                "category": e.category,
                "amount": str(e.amount),
                "currency": e.currency,
                "spent_on": e.spent_on.isoformat(),
                "note": e.note,
            }
            for e in expenses
        ],
        "goals": [
            {
                "id": str(g.id),
                "name": g.name,
                "target_amount": str(g.target_amount),
                "currency": g.currency,
                "target_date": g.target_date.isoformat(),
                "created_at": g.created_at.isoformat(),
            }
            for g in goals
        ],
        "risk_profile": (
            None
            if profile is None
            else {
                "crra_gamma": str(profile.crra_gamma),
                "crra_gamma_low": str(profile.crra_gamma_low),
                "crra_gamma_high": str(profile.crra_gamma_high),
                "assessed_at": profile.assessed_at.isoformat(),
            }
        ),
        "telegram": (None if tg is None else {"linked": tg.chat_id is not None}),
        "audit_log": [
            {
                "id": str(r.id),
                "action": r.action,
                "entity_type": r.entity_type,
                "entity_id": str(r.entity_id),
                "old_data": r.old_data,
                "new_data": r.new_data,
                "created_at": r.created_at.isoformat(),
            }
            for r in audit
        ],
    }


async def delete_account(db: AsyncSession, user: User, password: str) -> None:
    """Irreversible: re-verify password, audit the erasure (no PII in the row),
    then delete the user — cascading away all financial/PII data. The append-only
    audit log has no FK to users, so the trail survives, pseudonymised."""
    if not verify_password(password, user.password_hash):
        raise AppError("INVALID_CREDENTIALS", "Password is incorrect.", 401)
    await write_audit(
        db,
        actor_id=user.id,
        action="DELETE",
        entity_type="user",
        entity_id=user.id,  # no email / PII recorded in the deletion event
    )
    await db.delete(user)  # cascades: accounts->holdings, income, expenses, goals, ...
    await db.commit()
