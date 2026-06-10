import uuid
from collections.abc import AsyncGenerator, Callable
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.models import User
from backend.common.database import get_db
from backend.main import app

STRONG_PASSWORD = "Str0ng!Pass#99"


def _make_db_override(
    existing_user: object = None,
) -> Callable[[], AsyncGenerator[AsyncSession, None]]:
    async def override() -> AsyncGenerator[AsyncSession, None]:
        session = AsyncMock(spec=AsyncSession)
        session.scalar = AsyncMock(return_value=existing_user)
        session.add = MagicMock()
        session.commit = AsyncMock()

        async def _refresh(obj: object) -> None:
            # Simulate what the DB populates via server_default on INSERT
            if isinstance(obj, User):
                setattr(obj, "id", uuid.uuid4())
                setattr(obj, "created_at", datetime.now(timezone.utc))

        session.refresh = AsyncMock(side_effect=_refresh)
        yield session

    return override


def test_register_success() -> None:
    app.dependency_overrides[get_db] = _make_db_override(existing_user=None)
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "user@example.com", "password": STRONG_PASSWORD},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "user@example.com"
    assert "id" in body
    assert "password_hash" not in body


def test_register_duplicate_email() -> None:
    app.dependency_overrides[get_db] = _make_db_override(existing_user=MagicMock())
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "taken@example.com", "password": STRONG_PASSWORD},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 409
    assert resp.json()["code"] == "EMAIL_TAKEN"


def test_register_weak_password() -> None:
    app.dependency_overrides[get_db] = _make_db_override()
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "user@example.com", "password": "weak"},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 422
    assert resp.json()["code"] == "WEAK_PASSWORD"


def test_register_invalid_email() -> None:
    app.dependency_overrides[get_db] = _make_db_override()
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": STRONG_PASSWORD},
        )
    app.dependency_overrides.clear()

    # Pydantic rejects the email before the handler runs — FastAPI returns 422
    assert resp.status_code == 422
