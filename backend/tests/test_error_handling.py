
from fastapi.testclient import TestClient

from app.main import app


def test_http_error_includes_standardized_error_response(client):
    response = client.get("/route-that-does-not-exist")

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == "Not Found"
    assert data["error"]["code"] == "HTTP_404"
    assert data["error"]["message"] == "Not Found"
    assert data["error"]["details"] is None
    assert data["error"]["request_id"] == response.headers["X-Request-ID"]


def test_validation_error_includes_standardized_error_response(client):
    response = client.post(
        "/api/v1/auth/token",
        json={},
    )

    assert response.status_code == 422

    data = response.json()

    assert isinstance(data["detail"], list)
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert data["error"]["message"] == "Request validation failed"
    assert data["error"]["details"] == data["detail"]
    assert data["error"]["request_id"] == response.headers["X-Request-ID"]


def test_unexpected_error_returns_safe_500_response(monkeypatch):
    def raise_unexpected_error():
        raise RuntimeError("Internal database implementation details")

    monkeypatch.setattr(
        "app.main.engine.connect",
        raise_unexpected_error,
    )

    with TestClient(
        app,
        raise_server_exceptions=False,
    ) as test_client:
        response = test_client.get("/health/database")

    assert response.status_code == 500

    data = response.json()

    assert data["detail"] == "Internal server error"
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert data["error"]["message"] == "Internal server error"
    assert data["error"]["details"] is None
    assert "Internal database implementation details" not in response.text
    assert data["error"]["request_id"] == response.headers["X-Request-ID"]
