
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.models import Organization, WidgetSession


def register_widget_organization(client, email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Widget Owner",
            "email": email,
            "password": "OwnerPassword123!",
            "organization_name": "Widget Test Organization",
        },
    )

    assert response.status_code == 201

    organization = response.json()["organization"]

    return {
        "id": organization["id"],
        "public_key": organization["public_key"],
    }


def create_widget_session(client, public_key):
    response = client.post(
        f"/api/v1/widget/{public_key}/sessions"
    )

    return response


def widget_headers(session_token):
    return {
        "X-Widget-Session": session_token,
    }


def create_widget_conversation(client, public_key, session_token):
    return client.post(
        f"/api/v1/widget/{public_key}/conversations",
        headers=widget_headers(session_token),
        json={
            "full_name": "Test Visitor",
            "email": None,
            "subject": "Widget security test",
            "message": "I need assistance.",
        },
    )


def test_widget_session_rate_limit(client, monkeypatch):
    monkeypatch.setattr(
        settings,
        "widget_session_rate_limit",
        2,
    )

    organization = register_widget_organization(
        client,
        "widget_limit@example.com",
    )

    first = create_widget_session(
        client,
        organization["public_key"],
    )

    second = create_widget_session(
        client,
        organization["public_key"],
    )

    third = create_widget_session(
        client,
        organization["public_key"],
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert third.status_code == 429

    assert "Retry-After" in third.headers


def test_widget_session_rate_limit_is_organization_scoped(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "widget_session_rate_limit",
        1,
    )

    organization_one = register_widget_organization(
        client,
        "widget_org_one@example.com",
    )

    organization_two = register_widget_organization(
        client,
        "widget_org_two@example.com",
    )

    first = create_widget_session(
        client,
        organization_one["public_key"],
    )

    blocked = create_widget_session(
        client,
        organization_one["public_key"],
    )

    independent = create_widget_session(
        client,
        organization_two["public_key"],
    )

    assert first.status_code == 201
    assert blocked.status_code == 429
    assert independent.status_code == 201


def test_widget_conversation_rate_limit(
    client,
    monkeypatch,
):
    from app.api.v1.endpoints import widget

    monkeypatch.setattr(
        settings,
        "widget_conversation_rate_limit",
        2,
    )

    monkeypatch.setattr(
        widget,
        "process_widget_ai",
        lambda **kwargs: None,
    )

    organization = register_widget_organization(
        client,
        "widget_conversation_limit@example.com",
    )

    session_response = create_widget_session(
        client,
        organization["public_key"],
    )

    assert session_response.status_code == 201

    session_token = session_response.json()["session_token"]

    first = create_widget_conversation(
        client,
        organization["public_key"],
        session_token,
    )

    second = create_widget_conversation(
        client,
        organization["public_key"],
        session_token,
    )

    third = create_widget_conversation(
        client,
        organization["public_key"],
        session_token,
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert third.status_code == 429


def test_widget_message_rate_limit(
    client,
    monkeypatch,
):
    from app.api.v1.endpoints import widget

    monkeypatch.setattr(
        settings,
        "widget_message_rate_limit",
        2,
    )

    monkeypatch.setattr(
        widget,
        "process_widget_ai",
        lambda **kwargs: None,
    )

    organization = register_widget_organization(
        client,
        "widget_message_limit@example.com",
    )

    session_response = create_widget_session(
        client,
        organization["public_key"],
    )

    assert session_response.status_code == 201

    session_token = session_response.json()["session_token"]

    conversation_response = create_widget_conversation(
        client,
        organization["public_key"],
        session_token,
    )

    assert conversation_response.status_code == 201

    headers = widget_headers(session_token)

    first = client.post(
        f"/api/v1/widget/{organization['public_key']}/messages",
        headers=headers,
        json={"message": "First follow-up message"},
    )

    second = client.post(
        f"/api/v1/widget/{organization['public_key']}/messages",
        headers=headers,
        json={"message": "Second follow-up message"},
    )

    third = client.post(
        f"/api/v1/widget/{organization['public_key']}/messages",
        headers=headers,
        json={"message": "Third follow-up message"},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert third.status_code == 429


def test_widget_session_cannot_be_used_with_another_organization(
    client,
):
    organization_one = register_widget_organization(
        client,
        "widget_session_owner_one@example.com",
    )

    organization_two = register_widget_organization(
        client,
        "widget_session_owner_two@example.com",
    )

    session_response = create_widget_session(
        client,
        organization_one["public_key"],
    )

    assert session_response.status_code == 201

    session_token = session_response.json()["session_token"]

    response = client.post(
        f"/api/v1/widget/{organization_two['public_key']}/conversations",
        headers=widget_headers(session_token),
        json={
            "full_name": "Unauthorized Visitor",
            "email": None,
            "subject": "Cross organization attempt",
            "message": "This should not work.",
        },
    )

    assert response.status_code == 401


def test_expired_widget_session_is_rejected(
    client,
    db_session,
):
    organization = register_widget_organization(
        client,
        "widget_expired_session@example.com",
    )

    session_response = create_widget_session(
        client,
        organization["public_key"],
    )

    assert session_response.status_code == 201

    session_token = session_response.json()["session_token"]

    from app.services.widget_service import _hash_token

    session = db_session.query(WidgetSession).filter(
        WidgetSession.token_hash == _hash_token(session_token)
    ).one()

    session.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.commit()

    response = client.post(
        f"/api/v1/widget/{organization['public_key']}/conversations",
        headers=widget_headers(session_token),
        json={
            "full_name": "Expired Visitor",
            "email": None,
            "subject": "Expired session test",
            "message": "This should be rejected.",
        },
    )

    assert response.status_code == 401
