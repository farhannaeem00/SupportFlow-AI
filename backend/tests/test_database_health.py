
from sqlalchemy.exc import SQLAlchemyError


def test_database_health_returns_healthy_when_database_is_available(client):
    response = client.get("/health/database")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "database": "connected",
    }


def test_database_health_returns_503_when_database_is_unavailable(
    client,
    monkeypatch,
):
    def raise_database_error():
        raise SQLAlchemyError("Simulated database failure")

    monkeypatch.setattr(
        "app.main.engine.connect",
        raise_database_error,
    )

    response = client.get("/health/database")

    assert response.status_code == 503

    data = response.json()

    assert data["detail"] == "Database unavailable"
    assert data["error"]["code"] == "HTTP_503"
    assert data["error"]["message"] == "Database unavailable"
    assert data["error"]["details"] is None

    assert data["error"]["request_id"] == response.headers["X-Request-ID"]
