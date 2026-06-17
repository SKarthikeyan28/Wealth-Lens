import hmac
import os

from backend.common.errors import AppError


def verify_webhook_secret(provided: str | None) -> None:
    """Constant-time check of the X-Telegram-Bot-Api-Secret-Token header against
    our configured secret. Fail closed: if the secret is unset, reject all."""
    expected = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
    if not expected or not provided or not hmac.compare_digest(provided, expected):
        raise AppError("TELEGRAM_FORBIDDEN", "Invalid webhook secret.", 403)
