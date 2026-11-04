def test_request_logging_adds_request_id_header(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers

    request_id = response.headers["X-Request-ID"]

    assert len(request_id) == 36


def test_request_logging_generates_unique_request_ids(client):
    first_response = client.get("/health")
    second_response = client.get("/health")

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_id = first_response.headers["X-Request-ID"]
    second_id = second_response.headers["X-Request-ID"]

    assert first_id != second_id


def test_request_logging_preserves_response(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == (
        "Welcome to SupportFlow AI API"
    )
    assert response.headers.get("X-Request-ID")