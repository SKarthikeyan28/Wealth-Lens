import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt

_ALGORITHM = "HS256"
_PREAUTH_EXPIRE_MINUTES = 5


def _secret() -> str:
    return os.environ.get("JWT_SECRET_KEY", "")


def _access_expire_minutes() -> int:
    return int(os.environ.get("JWT_ACCESS_EXPIRE_MINUTES", "15"))


def _refresh_expire_days() -> int:
    return int(os.environ.get("JWT_REFRESH_EXPIRE_DAYS", "7"))


def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=_access_expire_minutes()),
    }
    return jwt.encode(payload, _secret(), algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict[str, object]:
    """Raises jwt.PyJWTError on invalid or expired token."""
    payload: dict[str, object] = jwt.decode(token, _secret(), algorithms=[_ALGORITHM])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Not an access token.")
    return payload


def create_preauth_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "pre-auth",
        "iat": now,
        "exp": now + timedelta(minutes=_PREAUTH_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, _secret(), algorithm=_ALGORITHM)


def decode_preauth_token(token: str) -> dict[str, object]:
    """Raises jwt.PyJWTError on invalid or expired token."""
    payload: dict[str, object] = jwt.decode(token, _secret(), algorithms=[_ALGORITHM])
    if payload.get("type") != "pre-auth":
        raise jwt.InvalidTokenError("Not a pre-auth token.")
    return payload


def generate_refresh_token() -> str:
    """Cryptographically random opaque string (not a JWT)."""
    return secrets.token_urlsafe(32)


def refresh_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=_refresh_expire_days())
