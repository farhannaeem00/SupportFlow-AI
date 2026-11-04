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
    assert response.json() == {
        "detail": "Database unavailable",
    }