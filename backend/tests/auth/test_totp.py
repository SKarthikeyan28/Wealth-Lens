import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.models import RecoveryCode, User
from backend.auth.tokens import create_preauth_token
from backend.common.database import get_db
from backend.main import app

_USER_ID = uuid.uuid4()


def _make_user(totp_enabled: bool = False, totp_secret: str | None = None) -> User:
    u = MagicMock(spec=User)
    u.id = _USER_ID
    u.email = "user@example.com"
    u.totp_enabled = totp_enabled
    u.totp_secret = (
        totp_secret if totp_secret is not None else ("encrypted" if totp_enabled else None)
    )
    u.created_at = datetime.now(timezone.utc)
    return u


def _make_recovery_code(used: bool = False) -> RecoveryCode:
    rc = MagicMock(spec=RecoveryCode)
    rc.user_id = _USER_ID
    rc.used = used
    return rc


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


def _make_db_multi(
    scalar_returns: list[object],
) -> Callable[[], AsyncGenerator[AsyncSession, None]]:
    async def override() -> AsyncGenerator[AsyncSession, None]:
        session = AsyncMock(spec=AsyncSession)
        session.scalar = AsyncMock(side_effect=scalar_returns)
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.execute = AsyncMock()
        yield session

    return override


def _auth_override(user: User) -> Callable[[], Awaitable[User]]:
    async def override() -> User:
        return user

    return override


# --- Login 2FA flag ---

def test_login_returns_preauth_when_2fa_enabled() -> None:
    user = _make_user(totp_enabled=True, totp_secret="encrypted")
    app.dependency_overrides[get_db] = _make_db(scalar_return=user)
    with patch("backend.auth.service.verify_password", return_value=True):
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": "user@example.com", "password": "Str0ng!Pass#99"},
            )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["requires_2fa"] is True
    assert body["pre_auth_token"] is not None
    assert body["access_token"] is None


def test_login_returns_tokens_when_2fa_disabled() -> None:
    user = _make_user(totp_enabled=False)
    app.dependency_overrides[get_db] = _make_db(scalar_return=user)
    with patch("backend.auth.service.verify_password", return_value=True):
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": "user@example.com", "password": "Str0ng!Pass#99"},
            )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["requires_2fa"] is False
    assert body["access_token"] is not None
    assert body["refresh_token"] is not None


# --- Enrol ---

def test_enroll_totp_returns_uri_and_secret() -> None:
    user = _make_user()
    app.dependency_overrides[get_db] = _make_db()
    app.dependency_overrides[get_current_user] = _auth_override(user)
    with patch("backend.auth.service.pyotp.random_base32", return_value="JBSWY3DPEHPK3PXP"):
        with patch("backend.auth.service.encrypt", return_value="encrypted-secret"):
            with TestClient(app) as client:
                resp = client.post("/api/v1/auth/totp/enroll")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert "provisioning_uri" in body
    assert body["secret"] == "JBSWY3DPEHPK3PXP"


# --- Confirm ---

def test_confirm_totp_valid_returns_recovery_codes() -> None:
    user = _make_user(totp_secret="encrypted")
    app.dependency_overrides[get_db] = _make_db()
    app.dependency_overrides[get_current_user] = _auth_override(user)
    with patch("backend.auth.service.decrypt", return_value="JBSWY3DPEHPK3PXP"):
        with patch("backend.auth.service.pyotp.TOTP") as mock_totp:
            mock_totp.return_value.verify.return_value = True
            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/auth/totp/confirm",
                    json={"totp_code": "123456"},
                )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["recovery_codes"]) == 8


def test_confirm_totp_invalid_code() -> None:
    user = _make_user(totp_secret="encrypted")
    app.dependency_overrides[get_db] = _make_db()
    app.dependency_overrides[get_current_user] = _auth_override(user)
    with patch("backend.auth.service.decrypt", return_value="JBSWY3DPEHPK3PXP"):
        with patch("backend.auth.service.pyotp.TOTP") as mock_totp:
            mock_totp.return_value.verify.return_value = False
            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/auth/totp/confirm",
                    json={"totp_code": "000000"},
                )
    app.dependency_overrides.clear()

    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_TOTP"


# --- Verify TOTP login ---

def test_verify_totp_valid() -> None:
    pre_auth = create_preauth_token(_USER_ID)
    user = _make_user(totp_enabled=True, totp_secret="encrypted")
    app.dependency_overrides[get_db] = _make_db(scalar_return=user)
    with patch("backend.auth.service.decrypt", return_value="JBSWY3DPEHPK3PXP"):
        with patch("backend.auth.service.pyotp.TOTP") as mock_totp:
            mock_totp.return_value.verify.return_value = True
            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/auth/totp/verify",
                    json={"pre_auth_token": pre_auth, "totp_code": "123456"},
                )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_verify_totp_invalid_code() -> None:
    pre_auth = create_preauth_token(_USER_ID)
    user = _make_user(totp_enabled=True, totp_secret="encrypted")
    app.dependency_overrides[get_db] = _make_db(scalar_return=user)
    with patch("backend.auth.service.decrypt", return_value="JBSWY3DPEHPK3PXP"):
        with patch("backend.auth.service.pyotp.TOTP") as mock_totp:
            mock_totp.return_value.verify.return_value = False
            with TestClient(app) as client:
                resp = client.post(
                    "/api/v1/auth/totp/verify",
                    json={"pre_auth_token": pre_auth, "totp_code": "000000"},
                )
    app.dependency_overrides.clear()

    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_TOTP"


# --- Recovery code login ---

def test_recover_valid_code() -> None:
    pre_auth = create_preauth_token(_USER_ID)
    user = _make_user(totp_enabled=True)
    rc = _make_recovery_code(used=False)
    app.dependency_overrides[get_db] = _make_db_multi([user, rc])
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/auth/totp/recover",
            json={"pre_auth_token": pre_auth, "recovery_code": "ABC123-DEF456"},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_recover_used_code_rejected() -> None:
    pre_auth = create_preauth_token(_USER_ID)
    user = _make_user(totp_enabled=True)
    app.dependency_overrides[get_db] = _make_db_multi([user, None])
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/auth/totp/recover",
            json={"pre_auth_token": pre_auth, "recovery_code": "ABC123-DEF456"},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_RECOVERY_CODE"
