import uuid
from collections.abc import AsyncGenerator, Callable
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.accounts.models import Account, Holding
from backend.auth.dependencies import get_current_user
from backend.auth.models import User
from backend.common.audit import AuditLog
from backend.common.database import get_db
from backend.main import app

USER_ID = uuid.uuid4()
ACCOUNT_ID = uuid.uuid4()


def _fake_user() -> User:
    u = User()
    u.id = USER_ID
    u.email = "you@example.com"
    return u


def _owned_account() -> Account:
    a = Account()
    a.id = ACCOUNT_ID
    a.user_id = USER_ID
    return a


def _db_override(
    scalar_results: list[object],
    added: list[object] | None = None,
) -> Callable[[], AsyncGenerator[AsyncSession, None]]:
    async def override() -> AsyncGenerator[AsyncSession, None]:
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock(side_effect=added.append) if added is not None else MagicMock()
        session.delete = AsyncMock()
        session.scalar = AsyncMock(side_effect=scalar_results)

        async def _commit() -> None:
            # Real Postgres populates server defaults (created_at) via RETURNING;
            # the mock has to do it by hand so HoldingResponse validates.
            for obj in added or []:
                if isinstance(obj, Holding) and obj.created_at is None:
                    obj.created_at = datetime.now(timezone.utc)

        session.commit = AsyncMock(side_effect=_commit)
        yield session

    return override


def _use_auth() -> None:
    app.dependency_overrides[get_current_user] = _fake_user


def test_create_holding_success_and_audit() -> None:
    _use_auth()
    added: list[object] = []
    # scalar calls in order: (1) account ownership -> account, (2) security lookup -> None (new)
    app.dependency_overrides[get_db] = _db_override([_owned_account(), None], added=added)
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/holdings",
            json={
                "account_id": str(ACCOUNT_ID),
                "ticker": "VWRA",
                "exchange": "LSE",
                "asset_class": "ETF",
                "currency": "USD",
                "quantity": "10",
                "avg_cost": "100.50",
            },
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 201
    assert any(isinstance(o, Holding) for o in added)
    assert any(isinstance(o, AuditLog) for o in added)


def test_create_holding_account_not_owned_404() -> None:
    _use_auth()
    app.dependency_overrides[get_db] = _db_override([None])  # ownership lookup misses
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/holdings",
            json={
                "account_id": str(uuid.uuid4()),
                "ticker": "VWRA",
                "asset_class": "ETF",
                "currency": "USD",
                "quantity": "1",
                "avg_cost": "1",
            },
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 404
    assert resp.json()["code"] == "ACCOUNT_NOT_FOUND"


def test_create_holding_rejects_negative_quantity() -> None:
    _use_auth()
    app.dependency_overrides[get_db] = _db_override([_owned_account()])
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/holdings",
            json={
                "account_id": str(ACCOUNT_ID),
                "ticker": "VWRA",
                "asset_class": "ETF",
                "currency": "USD",
                "quantity": "-5",
                "avg_cost": "1",
            },
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 422  # Pydantic boundary validation, ge=0
