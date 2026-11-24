from fastapi.testclient import TestClient

from engipilot_ai.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "commercepilot-api"}
    assert response.headers["X-Request-ID"]


def test_unknown_route() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/missing")
    assert response.status_code == 404


def test_openapi_uses_commercepilot_brand() -> None:
    with TestClient(app) as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "CommercePilot AI API"
