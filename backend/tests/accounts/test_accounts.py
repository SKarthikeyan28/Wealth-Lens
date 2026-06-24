import uuid
from collections.abc import AsyncGenerator, Callable
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.accounts.models import Account
from backend.auth.dependencies import get_current_user
from backend.auth.models import User
from backend.common.audit import AuditLog
from backend.common.database import get_db
from backend.main import app

USER_ID = uuid.uuid4()


def _fake_user() -> User:
    u = User()
    u.id = USER_ID
    u.email = "you@example.com"
    return u


def _db_override(
    scalar_result: object = None,
    added: list[object] | None = None,
) -> Callable[[], AsyncGenerator[AsyncSession, None]]:
    async def override() -> AsyncGenerator[AsyncSession, None]:
        session = AsyncMock(spec=AsyncSession)
        if added is not None:
            session.add = MagicMock(side_effect=added.append)
        else:
            session.add = MagicMock()
        session.delete = AsyncMock()
        session.flush = AsyncMock()
        session.commit = AsyncMock()
        session.scalar = AsyncMock(return_value=scalar_result)

        async def _refresh(obj: object) -> None:
            if isinstance(obj, Account):
                if obj.id is None:
                    obj.id = uuid.uuid4()
                obj.created_at = datetime.now(timezone.utc)

        session.refresh = AsyncMock(side_effect=_refresh)
        yield session

    return override


def _use_auth() -> None:
    app.dependency_overrides[get_current_user] = _fake_user


def test_create_account_success() -> None:
    _use_auth()
    app.dependency_overrides[get_db] = _db_override()
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/accounts",
            json={"name": "DBS Multiplier", "account_type": "CASH", "cash_balance": "1000.00"},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "DBS Multiplier"
    assert body["currency"] == "SGD"
    assert "user_id" not in body  # never leaked


def test_create_writes_audit_row() -> None:
    _use_auth()
    added: list[object] = []
    app.dependency_overrides[get_db] = _db_override(added=added)
    with TestClient(app) as client:
        client.post("/api/v1/accounts", json={"name": "X", "account_type": "CASH"})
    app.dependency_overrides.clear()

    assert any(isinstance(o, Account) for o in added)
    assert any(isinstance(o, AuditLog) for o in added)  # audit staged in same txn


def test_get_account_not_found_returns_404() -> None:
    _use_auth()
    app.dependency_overrides[get_db] = _db_override(scalar_result=None)  # missing / not owned
    with TestClient(app) as client:
        resp = client.get(f"/api/v1/accounts/{uuid.uuid4()}")
    app.dependency_overrides.clear()

    assert resp.status_code == 404
    assert resp.json()["code"] == "ACCOUNT_NOT_FOUND"


def test_create_rejects_negative_balance() -> None:
    _use_auth()
    app.dependency_overrides[get_db] = _db_override()
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/accounts",
            json={"name": "X", "account_type": "CASH", "cash_balance": "-5"},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 422  # Pydantic boundary validation, ge=0


def test_create_requires_auth() -> None:
    app.dependency_overrides[get_db] = _db_override()
    with TestClient(app) as client:
        resp = client.post("/api/v1/accounts", json={"name": "X", "account_type": "CASH"})
    app.dependency_overrides.clear()

    assert resp.status_code == 401  # no bearer token → HTTPBearer rejects (401 Unauthorized)
