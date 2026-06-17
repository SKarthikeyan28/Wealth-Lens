"""Outbound Telegram seam — swappable so tests never hit the network."""

from __future__ import annotations

import os
from typing import Protocol

import httpx


class TelegramUnavailable(Exception):
    """Sending a message to Telegram failed."""


class TelegramClient(Protocol):
    async def send_message(self, chat_id: int, text: str) -> None: ...


class HttpTelegramClient:
    def __init__(self, token: str | None = None) -> None:
        self._token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")

    async def send_message(self, chat_id: int, text: str) -> None:
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json={"chat_id": chat_id, "text": text})
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise TelegramUnavailable(str(exc)) from exc


_client: HttpTelegramClient | None = None


def get_telegram_client() -> HttpTelegramClient:
    global _client
    if _client is None:
        _client = HttpTelegramClient()
    return _client
