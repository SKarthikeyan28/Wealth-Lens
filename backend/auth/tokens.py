import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt

_SECRET: str = os.environ.get("JWT_SECRET_KEY", "")
_ALGORITHM = "HS256"
_ACCESS_EXPIRE_MINUTES = int(os.environ.get("JWT_ACCESS_EXPIRE_MINUTES", "15"))
_REFRESH_EXPIRE_DAYS = int(os.environ.get("JWT_REFRESH_EXPIRE_DAYS", "7"))


def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=_ACCESS_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict[str, object]:
    """Raises jwt.PyJWTError on invalid or expired token."""
    payload: dict[str, object] = jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Not an access token.")
    return payload


def generate_refresh_token() -> str:
    """Cryptographically random opaque string (not a JWT)."""
    return secrets.token_urlsafe(32)


def refresh_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=_REFRESH_EXPIRE_DAYS)
