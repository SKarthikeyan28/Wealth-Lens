from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_ping_returns_ok() -> None:
    response = client.get("/api/v1/ping")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
