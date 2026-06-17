"""Explicit prompt-construction layer.

Kept separate from the network call so the entire outbound payload is a plain
object a test can introspect (see the PII-guard test). The system prompt also
carries the educational / analysis-not-advice framing — auditable in one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from backend.chatbot.summary import FinancialSummary

SYSTEM_PROMPT = (
    "You are Wealth-Lens, an educational personal-finance assistant for an "
    "individual in Singapore. You explain and analyse the user's finances using "
    "ONLY the summary figures provided in the user message. "
    "You provide analysis and education, NOT financial advice: never recommend "
    "specific products, never tell the user to buy or sell, and remind them that "
    "this is a simulation and they are responsible for their own decisions. "
    "If a question cannot be answered from the provided summary, say so plainly "
    "rather than inventing figures. Keep answers concise and clear."
)


@dataclass(frozen=True)
class Prompt:
    """The complete outbound payload, as plain data."""

    system: str
    messages: list[dict[str, str]]


def _fmt_money(value: Decimal, currency: str) -> str:
    return f"{currency} {value:,.2f}"


def _fmt_pct(value: Decimal | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def render_summary(summary: FinancialSummary) -> str:
    """A plain-text block of aggregates — the only finance data sent to the LLM."""
    ccy = summary.base_currency
    lines = [
        f"As-of date: {summary.as_of.isoformat()}",
        f"Net worth: {_fmt_money(summary.net_worth, ccy)}",
        f"Savings rate: {_fmt_pct(summary.savings_rate)}",
        f"Monthly expenses: {_fmt_money(summary.monthly_expenses, ccy)}",
        (
            "Emergency runway: n/a"
            if summary.runway_months is None
            else f"Emergency runway: {summary.runway_months:.1f} months"
        ),
        (
            "Years to financial independence: n/a"
            if summary.years_to_fi is None
            else f"Years to financial independence: {summary.years_to_fi:.1f}"
        ),
    ]
    if summary.allocation:
        lines.append("Allocation by asset class (weights):")
        for slice_ in summary.allocation:
            lines.append(f"  - {slice_.asset_class}: {_fmt_pct(slice_.weight)}")
    return "\n".join(lines)


def build_prompt(summary: FinancialSummary, question: str) -> Prompt:
    content = (
        "Here is a summary of my finances:\n"
        f"{render_summary(summary)}\n\n"
        f"Question: {question}"
    )
    return Prompt(system=SYSTEM_PROMPT, messages=[{"role": "user", "content": content}])
