
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, parse_qs

from sqlalchemy import select

from app.core.security import verify_password
from app.models import PasswordResetToken, User
from app.services.password_reset_service import (
    create_password_reset_token,
    hash_reset_token,
)
from app.config import settings


REQUEST_URL = "/api/v1/auth/password-reset/request"
CONFIRM_URL = "/api/v1/auth/password-reset/confirm"

PASSWORD = "TestPassword123!"
NEW_PASSWORD = "NewPassword456!"


def register_test_user(client, email="resetuser@example.com"):
    payload = {
        "full_name": "Reset Test User",
        "email": email,
        "password": PASSWORD,
        "organization_name": "Reset Test Organization",
    }

    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    return payload


def request_reset(client, email):
    return client.post(REQUEST_URL, json={"email": email})


def extract_token(reset_url):
    return parse_qs(urlparse(reset_url).query)["token"][0]


def test_password_reset_request_sends_email(client, monkeypatch):
    register_test_user(client)

    sent_emails = []

    def mock_send_email(to_email, reset_url):
        sent_emails.append((to_email, reset_url))

    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.send_password_reset_email",
        mock_send_email,
    )

    response = request_reset(client, "resetuser@example.com")

    assert response.status_code == 200
    assert "If an account exists" in response.json()["message"]

    assert len(sent_emails) == 1

    email, reset_url = sent_emails[0]
    assert email == "resetuser@example.com"

    raw_token = extract_token(reset_url)
    assert len(raw_token) >= 32



def test_password_reset_unknown_email_has_generic_response(
    client,
    monkeypatch,
):
    sent_emails = []

    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.send_password_reset_email",
        lambda *args: sent_emails.append(args),
    )

    response = request_reset(client, "unknown@example.com")

    assert response.status_code == 200
    assert response.json()["message"] == (
        "If an account exists with that email, "
        "password reset instructions will be sent."
    )
    assert sent_emails == []


def test_password_reset_success_and_new_password_login(
    client,
    monkeypatch,
):
    register_test_user(client)

    sent_emails = []

    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.send_password_reset_email",
        lambda email, url: sent_emails.append((email, url)),
    )

    request_response = request_reset(client, "resetuser@example.com")
    assert request_response.status_code == 200

    raw_token = extract_token(sent_emails[0][1])

    response = client.post(
        CONFIRM_URL,
        json={
            "token": raw_token,
            "new_password": NEW_PASSWORD,
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == (
        "Password reset successfully. You can now sign in."
    )

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "resetuser@example.com",
            "password": NEW_PASSWORD,
        },
    )

    assert login_response.status_code == 200

    old_password_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "resetuser@example.com",
            "password": PASSWORD,
        },
    )

    assert old_password_response.status_code == 401


def test_password_reset_token_cannot_be_reused(client, monkeypatch):
    register_test_user(client)

    sent_emails = []

    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.send_password_reset_email",
        lambda email, url: sent_emails.append(url),
    )

    request_reset(client, "resetuser@example.com")
    raw_token = extract_token(sent_emails[0])

    payload = {
        "token": raw_token,
        "new_password": NEW_PASSWORD,
    }

    first_response = client.post(CONFIRM_URL, json=payload)
    second_response = client.post(CONFIRM_URL, json=payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 400


def test_password_reset_rejects_invalid_token(client):
    response = client.post(
        CONFIRM_URL,
        json={
            "token": "invalid-token-" + ("x" * 32),
            "new_password": NEW_PASSWORD,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Invalid or expired password reset token."
    )


def test_password_reset_rejects_expired_token(
    client,
    db_session,
):
    payload = register_test_user(client)

    user = db_session.scalar(
        select(User).where(User.email == payload["email"])
    )

    raw_token = create_password_reset_token(db_session, user)

    reset_record = db_session.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_reset_token(raw_token)
        )
    )

    reset_record.expires_at = datetime.now(timezone.utc) - timedelta(
        minutes=1
    )
    db_session.commit()

    response = client.post(
        CONFIRM_URL,
        json={
            "token": raw_token,
            "new_password": NEW_PASSWORD,
        },
    )

    assert response.status_code == 400

    db_session.refresh(user)
    assert verify_password(PASSWORD, user.hashed_password)


def test_password_reset_invalidates_previous_tokens(
    client,
    monkeypatch,
    db_session,
):
    payload = register_test_user(client)

    user = db_session.scalar(
        select(User).where(User.email == payload["email"])
    )

    first_token = create_password_reset_token(db_session, user)
    second_token = create_password_reset_token(db_session, user)

    first_record = db_session.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_reset_token(first_token)
        )
    )

    assert first_record.used_at is not None

    response = client.post(
        CONFIRM_URL,
        json={
            "token": second_token,
            "new_password": NEW_PASSWORD,
        },
    )

    assert response.status_code == 200


def test_password_reset_does_not_send_email_to_inactive_user(
    client,
    db_session,
    monkeypatch,
):
    payload = register_test_user(client)

    user = db_session.scalar(
        select(User).where(User.email == payload["email"])
    )

    user.is_active = False
    db_session.commit()

    sent_emails = []

    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.send_password_reset_email",
        lambda *args: sent_emails.append(args),
    )

    response = request_reset(client, payload["email"])

    assert response.status_code == 200
    assert sent_emails == []


def test_password_reset_rate_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "password_reset_rate_limit", 1)

    first = request_reset(client, "first-reset@example.com")
    second = request_reset(client, "second-reset@example.com")

    assert first.status_code == 200
    assert second.status_code == 429
    assert "Retry-After" in second.headers
