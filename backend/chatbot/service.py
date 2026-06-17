from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.models import User
from backend.chatbot.client import ChatbotUnavailable, LLMClient, get_client
from backend.chatbot.prompt import build_prompt
from backend.chatbot.summary import FinancialSummary, build_summary
from backend.common.errors import AppError

MAX_QUESTION_LEN = 1000


async def answer(
    db: AsyncSession,
    user: User,
    question: str,
    base_currency: str,
    as_of: date,
    client: LLMClient | None = None,
) -> str:
    """Build the user's derived summary, then delegate to `respond`. The DB and
    User are confined to this function — everything downstream sees aggregates
    only (the privacy boundary)."""
    summary = await build_summary(db, user.id, base_currency, as_of)
    return await respond(summary, question, client)


async def respond(
    summary: FinancialSummary,
    question: str,
    client: LLMClient | None = None,
) -> str:
    """Pure of DB/User: prompt-build → LLM call → graceful error mapping. This is
    the unit-testable seam — it takes a derived summary, never raw records."""
    question = question.strip()
    if not question:
        raise AppError("EMPTY_QUESTION", "Question must not be empty.", 422)
    if len(question) > MAX_QUESTION_LEN:
        raise AppError("QUESTION_TOO_LONG", "Question is too long.", 422)

    prompt = build_prompt(summary, question)

    client = client or get_client()
    try:
        return await client.complete(prompt)
    except ChatbotUnavailable:
        raise AppError(
            "CHATBOT_UNAVAILABLE",
            "The assistant is temporarily unavailable. Please try again shortly.",
            503,
        )
