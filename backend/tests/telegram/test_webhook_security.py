"""Webhook authenticity: the secret token is the auth boundary, not the URL."""

from __future__ import annotations

import pytest

from backend.common.errors import AppError
from backend.telegram.security import verify_webhook_secret

SECRET = "s3cret-token"


def test_correct_secret_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", SECRET)
    verify_webhook_secret(SECRET)  # must not raise


def test_wrong_secret_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", SECRET)
    with pytest.raises(AppError) as exc:
        verify_webhook_secret("forged")
    assert exc.value.status_code == 403


def test_missing_header_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", SECRET)
    with pytest.raises(AppError):
        verify_webhook_secret(None)


def test_unset_secret_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
    with pytest.raises(AppError):
        verify_webhook_secret(SECRET)
