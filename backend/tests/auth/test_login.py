import uuid
from collections.abc import AsyncGenerator, Callable
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.models import RefreshToken, User
from backend.common.database import get_db
from backend.main import app

_USER_ID = uuid.uuid4()
_FAMILY_ID = uuid.uuid4()
_REFRESH_VALUE = "test-refresh-token-abc123"


def _make_user() -> User:
    u = MagicMock(spec=User)
    u.id = _USER_ID
    u.email = "user@example.com"
    u.password_hash = "argon2-hash-placeholder"
    u.created_at = datetime.now(timezone.utc)
    return u


def _make_refresh_token(
    consumed: bool = False,
    revoked: bool = False,
    expires_at: datetime | None = None,
) -> RefreshToken:
    rt = MagicMock(spec=RefreshToken)
    rt.user_id = _USER_ID
    rt.family_id = _FAMILY_ID
    rt.consumed = consumed
    rt.revoked = revoked
    rt.expires_at = expires_at or datetime.now(timezone.utc) + timedelta(days=7)
    return rt


def _make_db(
    scalar_return: object = None,
) -> Callable[[], AsyncGenerator[AsyncSession, None]]:
    async def override() -> AsyncGenerator[AsyncSession, None]:
        session = AsyncMock(spec=AsyncSession)
        session.scalar = AsyncMock(return_value=scalar_return)
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.execute = AsyncMock()
        yield session

    return override


def test_login_success() -> None:
    app.dependency_overrides[get_db] = _make_db(scalar_return=_make_user())
    with patch("backend.auth.service.verify_password", return_value=True):
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": "user@example.com", "password": "Str0ng!Pass#99"},
            )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password() -> None:
    app.dependency_overrides[get_db] = _make_db(scalar_return=_make_user())
    with patch("backend.auth.service.verify_password", return_value=False):
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": "user@example.com", "password": "wrongpassword"},
            )
    app.dependency_overrides.clear()

    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_CREDENTIALS"


def test_login_unknown_email() -> None:
    app.dependency_overrides[get_db] = _make_db(scalar_return=None)
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "Str0ng!Pass#99"},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_CREDENTIALS"


def test_refresh_success() -> None:
    app.dependency_overrides[get_db] = _make_db(scalar_return=_make_refresh_token())
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": _REFRESH_VALUE},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_refresh_reuse_detected() -> None:
    app.dependency_overrides[get_db] = _make_db(
        scalar_return=_make_refresh_token(consumed=True)
    )
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": _REFRESH_VALUE},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 401
    assert resp.json()["code"] == "SECURITY_EVENT"


def test_refresh_expired() -> None:
    expired = datetime.now(timezone.utc) - timedelta(hours=1)
    app.dependency_overrides[get_db] = _make_db(
        scalar_return=_make_refresh_token(expires_at=expired)
    )
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": _REFRESH_VALUE},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_TOKEN"


def test_logout_consumes_token() -> None:
    app.dependency_overrides[get_db] = _make_db(scalar_return=_make_refresh_token())
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": _REFRESH_VALUE},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 204
