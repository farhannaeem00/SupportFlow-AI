
def register_test_user(client):
    payload = {
        "full_name": "Test User",
        "email": "testuser@example.com",
        "password": "TestPassword123!",
        "organization_name": "Test Organization",
    }

    response = client.post("/api/v1/auth/register", json=payload)
    return response, payload


def test_register_user_success(client):
    response, payload = register_test_user(client)

    assert response.status_code == 201

    data = response.json()

    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == payload["email"]
    assert data["user"]["full_name"] == payload["full_name"]
    assert data["organization"]["name"] == payload["organization_name"]


def test_login_success(client):
    _, payload = register_test_user(client)

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": payload["email"],
            "password": payload["password"],
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["access_token"]
    assert data["user"]["email"] == payload["email"]
    assert data["organization"]["name"] == payload["organization_name"]


def test_login_invalid_password(client):
    _, payload = register_test_user(client)

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": payload["email"],
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_get_current_user_success(client):
    register_response, _ = register_test_user(client)

    token = register_response.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "testuser@example.com"
    assert response.json()["full_name"] == "Test User"


def test_get_current_user_without_token(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_oauth2_token_success(client):
    _, payload = register_test_user(client)

    response = client.post(
        "/api/v1/auth/token",
        data={
            "username": payload["email"],
            "password": payload["password"],
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["access_token"]
    assert data["token_type"] == "bearer"


def test_register_invalid_email(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "invalid-email",
            "password": "TestPassword123!",
            "organization_name": "Test Organization",
        },
    )

    assert response.status_code == 422
