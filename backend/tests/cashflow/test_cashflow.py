import uuid
from collections.abc import AsyncGenerator, Callable
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_current_user
from backend.auth.models import User
from backend.cashflow.models import Expense, Income
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
        session.commit = AsyncMock()
        session.scalar = AsyncMock(return_value=scalar_result)
        yield session

    return override


def _use_auth() -> None:
    app.dependency_overrides[get_current_user] = _fake_user


def test_create_income_success() -> None:
    _use_auth()
    app.dependency_overrides[get_db] = _db_override()
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/income",
            json={"amount": "5000.00", "received_on": "2026-06-01"},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 201
    body = resp.json()
    assert body["amount"] == "5000.00"
    assert body["source_type"] == "SALARY"  # default
    assert "user_id" not in body


def test_create_income_writes_audit() -> None:
    _use_auth()
    added: list[object] = []
    app.dependency_overrides[get_db] = _db_override(added=added)
    with TestClient(app) as client:
        client.post("/api/v1/income", json={"amount": "100", "received_on": "2026-06-01"})
    app.dependency_overrides.clear()

    assert any(isinstance(o, Income) for o in added)
    assert any(isinstance(o, AuditLog) for o in added)


def test_income_not_found_returns_404() -> None:
    _use_auth()
    app.dependency_overrides[get_db] = _db_override(scalar_result=None)
    with TestClient(app) as client:
        resp = client.get(f"/api/v1/income/{uuid.uuid4()}")
    app.dependency_overrides.clear()

    assert resp.status_code == 404
    assert resp.json()["code"] == "INCOME_NOT_FOUND"


def test_create_expense_success() -> None:
    _use_auth()
    added: list[object] = []
    app.dependency_overrides[get_db] = _db_override(added=added)
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/expenses",
            json={"category": "Groceries", "amount": "85.50", "spent_on": "2026-06-02"},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 201
    assert resp.json()["category"] == "Groceries"
    assert any(isinstance(o, Expense) for o in added)
    assert any(isinstance(o, AuditLog) for o in added)


def test_create_expense_rejects_negative_amount() -> None:
    _use_auth()
    app.dependency_overrides[get_db] = _db_override()
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/expenses",
            json={"category": "X", "amount": "-1", "spent_on": "2026-06-02"},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 422
