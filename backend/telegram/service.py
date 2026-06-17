from __future__ import annotations

import secrets
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.cashflow.service import create_expense
from backend.dashboard.service import cashflow_summary, net_worth
from backend.telegram.client import TelegramClient
from backend.telegram.commands import CommandError, parse_command, parse_expense_args
from backend.telegram.models import TelegramLink
from backend.telegram.schemas import TgUpdate

CODE_TTL = timedelta(minutes=10)

HELP_TEXT = (
    "Wealth-Lens bot. Commands:\n"
    "/link <code> — link this chat (get a code in the web app)\n"
    "/add_expense <amount> [category] [note] — log an expense\n"
    "/summary — your net worth & cash-flow summary"
)
NOT_LINKED = "This chat isn't linked yet. Generate a code in the web app, then send /link <code>."


async def create_link_code(db: AsyncSession, user_id: uuid.UUID) -> tuple[str, datetime]:
    """Issue (or refresh) a one-time link code for the authenticated web user."""
    code = secrets.token_hex(4)  # 8 hex chars — short enough to type
    expires_at = datetime.now(timezone.utc) + CODE_TTL
    link = await db.scalar(select(TelegramLink).where(TelegramLink.user_id == user_id))
    if link is None:
        link = TelegramLink(id=uuid.uuid4(), user_id=user_id)
        db.add(link)
    link.link_code = code
    link.code_expires_at = expires_at
    await db.commit()
    return code, expires_at


async def link_chat(db: AsyncSession, code: str, chat_id: int) -> bool:
    """Complete a link: bind chat_id to the code's owner, then consume the code."""
    link = await db.scalar(select(TelegramLink).where(TelegramLink.link_code == code))
    if link is None or link.code_expires_at is None:
        return False
    if link.code_expires_at < datetime.now(timezone.utc):
        return False
    # Refuse if this chat is already bound to a different user.
    other = await db.scalar(select(TelegramLink).where(TelegramLink.chat_id == chat_id))
    if other is not None and other.user_id != link.user_id:
        return False
    link.chat_id = chat_id
    link.link_code = None
    link.code_expires_at = None
    await db.commit()
    return True


async def resolve_user(db: AsyncSession, chat_id: int) -> uuid.UUID | None:
    link = await db.scalar(select(TelegramLink).where(TelegramLink.chat_id == chat_id))
    return link.user_id if link is not None else None


async def _format_summary(db: AsyncSession, user_id: uuid.UUID) -> str:
    on = date.today()
    nw = await net_worth(db, user_id, "SGD", on)
    cf = await cashflow_summary(db, user_id, "SGD", on)
    sr = f"{cf.savings_rate * 100:.1f}%" if cf.savings_rate is not None else "n/a"
    runway = f"{cf.runway_months:.1f} months" if cf.runway_months is not None else "n/a"
    return (
        "Wealth-Lens summary (SGD)\n"
        f"Net worth: {nw:,.2f}\n"
        f"Savings rate: {sr}\n"
        f"Emergency runway: {runway}"
    )


async def _dispatch(db: AsyncSession, chat_id: int, name: str, args: list[str]) -> str:
    if name in ("start", "help"):
        return HELP_TEXT
    if name == "link":
        if not args:
            return "Usage: /link <code> (generate a code in the web app)."
        ok = await link_chat(db, args[0], chat_id)
        return (
            "Linked! You can now use /add_expense and /summary."
            if ok
            else "Invalid or expired code."
        )

    user_id = await resolve_user(db, chat_id)
    if name == "add_expense":
        if user_id is None:
            return NOT_LINKED
        try:
            data = parse_expense_args(args)
        except CommandError as exc:
            return str(exc)
        await create_expense(db, user_id, data)
        return f"Added {data.currency} {data.amount} to {data.category}."
    if name == "summary":
        if user_id is None:
            return NOT_LINKED
        return await _format_summary(db, user_id)
    return f"Unknown command.\n{HELP_TEXT}"


async def handle_update(db: AsyncSession, client: TelegramClient, update: TgUpdate) -> None:
    """Parse one update, run the mapped command, and reply. Non-text updates are
    ignored. The reply is the single outbound point."""
    if update.message is None or not update.message.text:
        return
    chat_id = update.message.chat.id
    cmd = parse_command(update.message.text)
    reply = await _dispatch(db, chat_id, cmd.name, cmd.args)
    await client.send_message(chat_id, reply)
