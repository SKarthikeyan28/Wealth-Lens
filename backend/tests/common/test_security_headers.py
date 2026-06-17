from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_security_headers_present() -> None:
    resp = client.get("/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "no-referrer"
    assert "default-src 'none'" in resp.headers["Content-Security-Policy"]
    assert "max-age=" in resp.headers["Strict-Transport-Security"]
