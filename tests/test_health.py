from fastapi.testclient import TestClient

from engipilot_ai.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "engipilot-api"}
    assert response.headers["X-Request-ID"]


def test_unknown_route() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/missing")
    assert response.status_code == 404
