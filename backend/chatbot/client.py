"""LLM provider seam — the swappable interface and the Anthropic implementation.

Mirrors the infra-singleton pattern in common.cache. Every provider error is
translated to `ChatbotUnavailable` so the service layer degrades gracefully and
never leaks a raw third-party stack trace.
"""

from __future__ import annotations

import os
from typing import Protocol

import anthropic

from backend.chatbot.prompt import Prompt


class ChatbotUnavailable(Exception):
    """The LLM provider failed; the caller should degrade gracefully."""


class LLMClient(Protocol):
    async def complete(self, prompt: Prompt) -> str: ...


class AnthropicClient:
    """Non-streaming completion over a derived summary. Streaming + adaptive
    thinking are a deliberate future enhancement — a Q&A over a tiny summary
    needs neither, and non-streaming keeps the outbound payload simple to test."""

    def __init__(
        self,
        model: str | None = None,
        max_tokens: int = 1024,
        client: anthropic.AsyncAnthropic | None = None,
    ) -> None:
        self._model: str = model or os.environ.get("CHATBOT_MODEL") or "claude-opus-4-8"
        self._max_tokens = max_tokens
        # Resolves ANTHROPIC_API_KEY from the environment.
        self._client = client or anthropic.AsyncAnthropic()

    async def complete(self, prompt: Prompt) -> str:
        try:
            message = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=prompt.system,
                messages=prompt.messages,  # type: ignore[arg-type]
            )
        except anthropic.APIError as exc:  # network, 4xx, 5xx, rate limits
            raise ChatbotUnavailable(str(exc)) from exc
        return "".join(block.text for block in message.content if block.type == "text")


_client: AnthropicClient | None = None


def get_client() -> AnthropicClient:
    global _client
    if _client is None:
        _client = AnthropicClient()
    return _client
