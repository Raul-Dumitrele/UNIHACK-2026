from fastapi.testclient import TestClient

from backend.app.main import app


def test_health_ok():
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_cors_allows_configured_origin():
    with TestClient(app) as client:
        r = client.options(
            "/health",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
        )
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
