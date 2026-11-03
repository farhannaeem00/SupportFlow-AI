
from datetime import datetime, timedelta, timezone

from jose import jwt
from sqlalchemy import select

from app.config import settings
from app.models import Organization, OrganizationMember, User


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
    assert data["organizations"]
    assert data["organizations"][0]["name"] == payload["organization_name"]
    assert data["organizations"][0]["role"] == "owner"


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
    assert data["organizations"]
    assert data["organizations"][0]["name"] == payload["organization_name"]
    assert data["organizations"][0]["role"] == "owner"


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


def test_login_inactive_user(client, db_session):
    _, payload = register_test_user(client)

    user = db_session.scalar(
        select(User).where(User.email == payload["email"])
    )

    user.is_active = False
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": payload["email"],
            "password": payload["password"],
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_with_malformed_password_hash(client, db_session):
    _, payload = register_test_user(client)

    user = db_session.scalar(
        select(User).where(User.email == payload["email"])
    )

    user.hashed_password = "invalid-argon2-hash"
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": payload["email"],
            "password": payload["password"],
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

def test_get_current_user_with_invalid_token(client):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.token.value"},
    )

    assert response.status_code == 401


def test_get_current_user_with_expired_token(client):
    expired_token = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000001",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401


def test_get_current_user_with_missing_subject(client):
    token = jwt.encode(
        {
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_register_rejects_whitespace_only_full_name(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "   ",
            "email": "whitespace@example.com",
            "password": "TestPassword123!",
            "organization_name": "Test Organization",
        },
    )

    assert response.status_code == 422


def test_login_returns_all_user_organizations(client, db_session):
    _, payload = register_test_user(client)

    user = db_session.scalar(
        select(User).where(User.email == payload["email"])
    )

    second_organization = Organization(
        name="Second Organization",
        slug="second-organization",
    )
    db_session.add(second_organization)
    db_session.flush()

    second_membership = OrganizationMember(
        user_id=user.id,
        organization_id=second_organization.id,
        role="agent",
    )
    db_session.add(second_membership)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": payload["email"],
            "password": payload["password"],
        },
    )

    assert response.status_code == 200

    organizations = response.json()["organizations"]

    assert len(organizations) == 2

    organization_names = {
        organization["name"] for organization in organizations
    }

    assert organization_names == {
        "Test Organization",
        "Second Organization",
    }

    roles = {
        organization["name"]: organization["role"]
        for organization in organizations
    }

    assert roles["Test Organization"] == "owner"
    assert roles["Second Organization"] == "agent"


def test_register_rejects_whitespace_only_organization_name(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "whitespace@example.com",
            "password": "TestPassword123!",
            "organization_name": "   ",
        },
    )

    assert response.status_code == 422


def test_register_rejects_whitespace_only_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "whitespace@example.com",
            "password": "        ",
            "organization_name": "Test Organization",
        },
    )

    assert response.status_code == 422


def test_login_rejects_password_over_maximum_length(client):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "A" * 129,
        },
    )

    assert response.status_code == 422


def test_register_rejects_duplicate_email(client):
    _, payload = register_test_user(client)

    response = client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "An account with this email already exists"
    )

def test_register_rate_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_register_rate_limit", 2)

    for index in range(2):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Test User",
                "email": f"register{index}@example.com",
                "password": "TestPassword123!",
                "organization_name": f"Organization {index}",
            },
        )
        assert response.status_code == 201

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "register3@example.com",
            "password": "TestPassword123!",
            "organization_name": "Organization 3",
        },
    )

    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_login_rate_limit(client, monkeypatch):
    _, payload = register_test_user(client)

    monkeypatch.setattr(settings, "auth_login_rate_limit", 2)

    login_payload = {
        "email": payload["email"],
        "password": "WrongPassword123!",
    }

    assert client.post(
        "/api/v1/auth/login", json=login_payload
    ).status_code == 401

    assert client.post(
        "/api/v1/auth/login", json=login_payload
    ).status_code == 401

    response = client.post(
        "/api/v1/auth/login", json=login_payload
    )

    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_oauth2_token_rate_limit(client, monkeypatch):
    _, payload = register_test_user(client)

    monkeypatch.setattr(settings, "auth_token_rate_limit", 2)

    token_payload = {
        "username": payload["email"],
        "password": "WrongPassword123!",
    }

    assert client.post(
        "/api/v1/auth/token", data=token_payload
    ).status_code == 401

    assert client.post(
        "/api/v1/auth/token", data=token_payload
    ).status_code == 401

    response = client.post(
        "/api/v1/auth/token", data=token_payload
    )

    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_login_rate_limits_are_independent_per_email(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_login_rate_limit", 1)

    first_payload = {
        "email": "first@example.com",
        "password": "WrongPassword123!",
    }

    second_payload = {
        "email": "second@example.com",
        "password": "WrongPassword123!",
    }

    first_response = client.post(
        "/api/v1/auth/login",
        json=first_payload,
    )
    assert first_response.status_code == 401

    blocked_response = client.post(
        "/api/v1/auth/login",
        json=first_payload,
    )
    assert blocked_response.status_code == 429

    second_response = client.post(
        "/api/v1/auth/login",
        json=second_payload,
    )
    assert second_response.status_code == 401
