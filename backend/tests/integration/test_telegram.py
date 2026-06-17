"""End-to-end Telegram flow against real Postgres: link -> add_expense -> summary.

A fake outbound client captures replies so we assert behaviour without the network.
Proves the gate: an expense can be added from Telegram and a summary retrieved,
and that an UNLINKED chat is refused (the auth-linking boundary).
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.models import User
from backend.cashflow.models import Expense
from backend.telegram.models import TelegramLink
from backend.telegram.schemas import TgChat, TgMessage, TgUpdate
from backend.telegram.service import create_link_code, handle_update, link_chat, resolve_user


class FakeTelegramClient:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str) -> None:
        self.sent.append((chat_id, text))


def _update(chat_id: int, text: str) -> TgUpdate:
    return TgUpdate(update_id=1, message=TgMessage(chat=TgChat(id=chat_id), text=text))


@pytest.mark.asyncio
async def test_link_add_expense_and_summary(db_session: AsyncSession) -> None:
    db = db_session
    user_id = uuid.uuid4()
    chat_id = 5550000 + int(uuid.uuid4().int % 100000)
    db.add(User(id=user_id, email=f"tg-{uuid.uuid4().hex}@example.com", password_hash="x"))
    await db.commit()

    try:
        # 1. Authenticated web app issues a code; user links the chat.
        code, _expires = await create_link_code(db, user_id)
        assert await link_chat(db, code, chat_id) is True
        assert await resolve_user(db, chat_id) == user_id

        client = FakeTelegramClient()

        # 2. Add an expense from Telegram.
        await handle_update(db, client, _update(chat_id, "/add_expense 12.50 food lunch"))
        rows = list(
            await db.scalars(select(Expense).where(Expense.user_id == user_id))
        )
        assert len(rows) == 1
        assert rows[0].amount == Decimal("12.50")
        assert rows[0].category == "food"
        assert rows[0].note == "lunch"
        assert rows[0].spent_on == date.today()
        assert "12.50" in client.sent[-1][1]

        # 3. Get a summary.
        await handle_update(db, client, _update(chat_id, "/summary"))
        assert "Net worth" in client.sent[-1][1]
    finally:
        await db.execute(delete(Expense).where(Expense.user_id == user_id))
        await db.execute(delete(TelegramLink).where(TelegramLink.user_id == user_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


@pytest.mark.asyncio
async def test_unlinked_chat_cannot_add_expense(db_session: AsyncSession) -> None:
    db = db_session
    chat_id = 5660000 + int(uuid.uuid4().int % 100000)
    client = FakeTelegramClient()

    await handle_update(db, client, _update(chat_id, "/add_expense 50 rent"))

    # Refused, and nothing was written for this (unknown) chat.
    assert "isn't linked" in client.sent[-1][1]
    assert await resolve_user(db, chat_id) is None
