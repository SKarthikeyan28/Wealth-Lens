"""Phase 5.1 chatbot tests.

Anchors:
- The outbound payload carries ONLY derived aggregates — never PII (the gate).
- The FinancialSummary type structurally cannot hold a PII field.
- A provider failure degrades gracefully to a clean 503, never a leak.
- The happy path returns the model's answer.
"""

from __future__ import annotations

import dataclasses
from datetime import date
from decimal import Decimal

import anthropic
import pytest

from backend.chatbot.client import AnthropicClient, ChatbotUnavailable
from backend.chatbot.prompt import Prompt, build_prompt
from backend.chatbot.service import respond
from backend.chatbot.summary import AllocationWeight, FinancialSummary
from backend.common.errors import AppError

# PII that exists in raw records but must NEVER reach the LLM.
PII_SENTINELS = ("alice@example.com", "Alice Tan", "1234567890", "DBS-SAVINGS-001")

ALLOWED_SUMMARY_FIELDS = {
    "base_currency",
    "as_of",
    "net_worth",
    "allocation",
    "savings_rate",
    "monthly_expenses",
    "runway_months",
    "years_to_fi",
}


def _summary() -> FinancialSummary:
    return FinancialSummary(
        base_currency="SGD",
        as_of=date(2026, 6, 17),
        net_worth=Decimal("150000.00"),
        allocation=(
            AllocationWeight("CASH", Decimal("0.4000")),
            AllocationWeight("EQUITY", Decimal("0.6000")),
        ),
        savings_rate=Decimal("0.3200"),
        monthly_expenses=Decimal("3500.00"),
        runway_months=Decimal("12.5"),
        years_to_fi=18.4,
    )


def test_summary_type_holds_only_aggregate_fields() -> None:
    names = {f.name for f in dataclasses.fields(FinancialSummary)}
    assert names == ALLOWED_SUMMARY_FIELDS


def test_outbound_payload_contains_no_pii() -> None:
    prompt = build_prompt(_summary(), question="How is my savings rate?")
    blob = prompt.system + "".join(m["content"] for m in prompt.messages)
    for sentinel in PII_SENTINELS:
        assert sentinel not in blob
    # And it DID carry the aggregates we intend to send.
    assert "150,000.00" in blob
    assert "32.0%" in blob


class _FailingRawMessages:
    @staticmethod
    async def create(**_kwargs: object) -> object:
        raise anthropic.APIConnectionError(request=None)  # type: ignore[arg-type]


class _FailingRawClient:
    messages = _FailingRawMessages()


@pytest.mark.asyncio
async def test_client_translates_provider_error() -> None:
    client = AnthropicClient(client=_FailingRawClient())  # type: ignore[arg-type]
    with pytest.raises(ChatbotUnavailable):
        await client.complete(build_prompt(_summary(), question="hi"))


class _FailingClient:
    async def complete(self, prompt: Prompt) -> str:
        raise ChatbotUnavailable("boom")


class _OkClient:
    async def complete(self, prompt: Prompt) -> str:
        return "Your savings rate is healthy."


@pytest.mark.asyncio
async def test_respond_degrades_gracefully() -> None:
    with pytest.raises(AppError) as exc:
        await respond(_summary(), "hi", client=_FailingClient())
    assert exc.value.code == "CHATBOT_UNAVAILABLE"
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_respond_happy_path() -> None:
    out = await respond(_summary(), "How is my savings rate?", client=_OkClient())
    assert out == "Your savings rate is healthy."
