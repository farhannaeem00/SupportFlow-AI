
import socket
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select

from app.models.conversation_event import ConversationEvent
from app.models.webhook import WebhookDelivery, WebhookEndpoint
from app.services import webhook_security


def register_owner(client, email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Webhook Management Owner",
            "email": email,
            "password": "OwnerPassword123!",
            "organization_name": "Webhook Management Organization",
        },
    )
    assert response.status_code == 201

    data = response.json()
    return {
        "token": data["access_token"],
        "organization_id": uuid.UUID(data["organization"]["id"]),
        "user_id": uuid.UUID(data["user"]["id"]),
    }


def auth_headers(owner):
    return {
        "Authorization": f"Bearer {owner['token']}",
        "X-Organization-ID": str(owner["organization_id"]),
    }


def create_conversation(client, owner, email):
    headers = auth_headers(owner)

    customer_response = client.post(
        "/api/v1/customers",
        headers=headers,
        json={
            "full_name": "Webhook Management Customer",
            "email": email,
            "phone": "03001234567",
            "company": "Webhook Management Company",
        },
    )
    assert customer_response.status_code == 201

    conversation_response = client.post(
        "/api/v1/conversations",
        headers=headers,
        json={
            "customer_id": customer_response.json()["id"],
            "subject": "Webhook management test conversation",
            "priority": "normal",
            "channel": "web_widget",
        },
    )
    assert conversation_response.status_code == 201

    return uuid.UUID(conversation_response.json()["id"])


def create_endpoint(
    db_session,
    organization_id,
    subscribed_events=None,
    *,
    is_active=True,
    name="Test Webhook",
):
    endpoint = WebhookEndpoint(
        organization_id=organization_id,
        name=name,
        url="https://hooks.example.com/supportflow",
        encrypted_secret="test-encrypted-secret",
        subscribed_events=(
            subscribed_events
            if subscribed_events is not None
            else ["conversation.status_changed"]
        ),
        is_active=is_active,
    )
    db_session.add(endpoint)
    db_session.flush()
    return endpoint


def create_delivery(
    db_session,
    organization_id,
    endpoint_id,
    conversation_id,
    *,
    delivery_status="pending",
    attempt_count=0,
):
    event = ConversationEvent(
        conversation_id=conversation_id,
        event_type="status_changed",
        old_value="open",
        new_value="pending",
    )
    db_session.add(event)
    db_session.flush()

    delivery = WebhookDelivery(
        organization_id=organization_id,
        endpoint_id=endpoint_id,
        event_id=event.id,
        event_type="conversation.status_changed",
        payload={
            "event_id": str(event.id),
            "event_type": "conversation.status_changed",
            "organization_id": str(organization_id),
            "data": {
                "conversation_id": str(conversation_id),
            },
        },
        status=delivery_status,
        attempt_count=attempt_count,
        max_attempts=5,
        next_attempt_at=datetime.now(timezone.utc),
        last_attempt_at=(
            datetime.now(timezone.utc) - timedelta(minutes=2)
            if attempt_count
            else None
        ),
        response_status=500 if delivery_status == "failed" else None,
        response_body="Server error" if delivery_status == "failed" else None,
        last_error="HTTP 500" if delivery_status == "failed" else None,
    )
    db_session.add(delivery)
    db_session.flush()
    return delivery


def configure_webhook_security(monkeypatch):
    encryption_key = Fernet.generate_key().decode()

    monkeypatch.setattr(
        webhook_security.settings,
        "webhook_encryption_key",
        encryption_key,
    )

    def public_dns_result(*args, **kwargs):
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("93.184.216.34", 443),
            )
        ]

    monkeypatch.setattr(
        webhook_security.socket,
        "getaddrinfo",
        public_dns_result,
    )

    return encryption_key


def test_create_webhook_endpoint(client, monkeypatch):
    configure_webhook_security(monkeypatch)
    owner = register_owner(client, "webhook_management_create@example.com")

    response = client.post(
        "/api/v1/webhooks",
        headers=auth_headers(owner),
        json={
            "name": "CRM Events",
            "url": "https://hooks.example.com/events",
            "subscribed_events": [
                "conversation.created",
                "conversation.status_changed",
            ],
        },
    )

    assert response.status_code == 201

    data = response.json()
    endpoint = data["endpoint"]

    assert endpoint["name"] == "CRM Events"
    assert endpoint["organization_id"] == str(owner["organization_id"])
    assert endpoint["created_by_id"] == str(owner["user_id"])
    assert endpoint["url"] == "https://hooks.example.com/events"
    assert endpoint["subscribed_events"] == [
        "conversation.created",
        "conversation.status_changed",
    ]
    assert endpoint["is_active"] is True

    assert data["signing_secret"]
    assert len(data["signing_secret"]) >= 32
    assert "encrypted_secret" not in endpoint


def test_create_webhook_endpoint_strips_name(client, monkeypatch):
    configure_webhook_security(monkeypatch)
    owner = register_owner(client, "webhook_management_name@example.com")

    response = client.post(
        "/api/v1/webhooks",
        headers=auth_headers(owner),
        json={
            "name": "  CRM Events  ",
            "url": "https://hooks.example.com/events",
            "subscribed_events": ["conversation.created"],
        },
    )

    assert response.status_code == 201
    assert response.json()["endpoint"]["name"] == "CRM Events"


def test_create_webhook_rejects_unsupported_event(client, monkeypatch):
    configure_webhook_security(monkeypatch)
    owner = register_owner(client, "webhook_management_event@example.com")

    response = client.post(
        "/api/v1/webhooks",
        headers=auth_headers(owner),
        json={
            "name": "Invalid Events",
            "url": "https://hooks.example.com/events",
            "subscribed_events": ["conversation.unknown"],
        },
    )

    assert response.status_code == 422
    assert "unsupported" in response.text.lower()


def test_create_webhook_rejects_duplicate_events(client, monkeypatch):
    configure_webhook_security(monkeypatch)
    owner = register_owner(client, "webhook_management_duplicate@example.com")

    response = client.post(
        "/api/v1/webhooks",
        headers=auth_headers(owner),
        json={
            "name": "Duplicate Events",
            "url": "https://hooks.example.com/events",
            "subscribed_events": [
                "conversation.created",
                "conversation.created",
            ],
        },
    )

    assert response.status_code == 422


def test_create_webhook_rejects_insecure_url(client, monkeypatch):
    configure_webhook_security(monkeypatch)
    owner = register_owner(client, "webhook_management_url@example.com")

    response = client.post(
        "/api/v1/webhooks",
        headers=auth_headers(owner),
        json={
            "name": "Insecure URL",
            "url": "http://hooks.example.com/events",
            "subscribed_events": ["conversation.created"],
        },
    )

    assert response.status_code == 422


def test_list_webhook_endpoints_is_organization_scoped(
    client,
    db_session,
):
    owner_one = register_owner(
        client,
        "webhook_management_list_one@example.com",
    )
    owner_two = register_owner(
        client,
        "webhook_management_list_two@example.com",
    )

    first = create_endpoint(
        db_session,
        owner_one["organization_id"],
        name="Organization One Webhook",
    )
    create_endpoint(
        db_session,
        owner_two["organization_id"],
        name="Organization Two Webhook",
    )

    response = client.get(
        "/api/v1/webhooks",
        headers=auth_headers(owner_one),
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(first.id)
    assert data[0]["name"] == "Organization One Webhook"
    assert "encrypted_secret" not in data[0]


def test_list_webhook_endpoints_requires_authentication(client):
    response = client.get("/api/v1/webhooks")

    assert response.status_code == 401


def test_update_webhook_endpoint(client, db_session, monkeypatch):
    configure_webhook_security(monkeypatch)
    owner = register_owner(
        client,
        "webhook_management_update@example.com",
    )
    endpoint = create_endpoint(
        db_session,
        owner["organization_id"],
    )

    response = client.patch(
        f"/api/v1/webhooks/{endpoint.id}",
        headers=auth_headers(owner),
        json={
            "name": "Updated CRM Webhook",
            "subscribed_events": [
                "conversation.created",
                "conversation.assigned",
            ],
            "is_active": False,
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["id"] == str(endpoint.id)
    assert data["name"] == "Updated CRM Webhook"
    assert data["subscribed_events"] == [
        "conversation.created",
        "conversation.assigned",
    ]
    assert data["is_active"] is False


def test_update_webhook_endpoint_validates_url(
    client,
    db_session,
    monkeypatch,
):
    configure_webhook_security(monkeypatch)
    owner = register_owner(
        client,
        "webhook_management_update_url@example.com",
    )
    endpoint = create_endpoint(db_session, owner["organization_id"])

    response = client.patch(
        f"/api/v1/webhooks/{endpoint.id}",
        headers=auth_headers(owner),
        json={"url": "http://insecure.example.com/events"},
    )

    assert response.status_code == 422


def test_update_webhook_endpoint_rejects_empty_update(
    client,
    db_session,
):
    owner = register_owner(
        client,
        "webhook_management_empty_update@example.com",
    )
    endpoint = create_endpoint(db_session, owner["organization_id"])

    response = client.patch(
        f"/api/v1/webhooks/{endpoint.id}",
        headers=auth_headers(owner),
        json={},
    )

    assert response.status_code == 400


def test_update_webhook_endpoint_rejects_null_fields(
    client,
    db_session,
):
    owner = register_owner(
        client,
        "webhook_management_null_update@example.com",
    )
    endpoint = create_endpoint(db_session, owner["organization_id"])

    response = client.patch(
        f"/api/v1/webhooks/{endpoint.id}",
        headers=auth_headers(owner),
        json={"name": None},
    )

    assert response.status_code == 422


def test_update_webhook_endpoint_rejects_other_organization(
    client,
    db_session,
):
    owner_one = register_owner(
        client,
        "webhook_management_update_owner_one@example.com",
    )
    owner_two = register_owner(
        client,
        "webhook_management_update_owner_two@example.com",
    )
    endpoint = create_endpoint(db_session, owner_two["organization_id"])

    response = client.patch(
        f"/api/v1/webhooks/{endpoint.id}",
        headers=auth_headers(owner_one),
        json={"name": "Unauthorized Update"},
    )

    assert response.status_code == 404


def test_delete_webhook_endpoint(client, db_session):
    owner = register_owner(
        client,
        "webhook_management_delete@example.com",
    )
    endpoint = create_endpoint(db_session, owner["organization_id"])
    endpoint_id = endpoint.id

    response = client.delete(
        f"/api/v1/webhooks/{endpoint_id}",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Webhook endpoint deleted successfully"

    stored_endpoint = db_session.scalar(
        select(WebhookEndpoint).where(WebhookEndpoint.id == endpoint_id)
    )
    assert stored_endpoint is None


def test_delete_webhook_endpoint_rejects_other_organization(
    client,
    db_session,
):
    owner_one = register_owner(
        client,
        "webhook_management_delete_one@example.com",
    )
    owner_two = register_owner(
        client,
        "webhook_management_delete_two@example.com",
    )
    endpoint = create_endpoint(db_session, owner_two["organization_id"])

    response = client.delete(
        f"/api/v1/webhooks/{endpoint.id}",
        headers=auth_headers(owner_one),
    )

    assert response.status_code == 404


def test_rotate_webhook_secret(client, db_session, monkeypatch):
    encryption_key = configure_webhook_security(monkeypatch)
    owner = register_owner(
        client,
        "webhook_management_rotate@example.com",
    )
    endpoint = create_endpoint(db_session, owner["organization_id"])
    previous_encrypted_secret = endpoint.encrypted_secret

    response = client.post(
        f"/api/v1/webhooks/{endpoint.id}/rotate-secret",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200

    data = response.json()
    assert data["endpoint_id"] == str(endpoint.id)
    assert data["signing_secret"]
    assert data["signing_secret"] != previous_encrypted_secret

    db_session.refresh(endpoint)
    assert endpoint.encrypted_secret != previous_encrypted_secret

    decrypted_secret = Fernet(encryption_key.encode()).decrypt(
        endpoint.encrypted_secret.encode()
    ).decode()

    assert decrypted_secret == data["signing_secret"]


def test_rotate_secret_rejects_other_organization(client, db_session):
    owner_one = register_owner(
        client,
        "webhook_management_rotate_one@example.com",
    )
    owner_two = register_owner(
        client,
        "webhook_management_rotate_two@example.com",
    )
    endpoint = create_endpoint(db_session, owner_two["organization_id"])

    response = client.post(
        f"/api/v1/webhooks/{endpoint.id}/rotate-secret",
        headers=auth_headers(owner_one),
    )

    assert response.status_code == 404


def test_list_webhook_deliveries(client, db_session):
    owner = register_owner(
        client,
        "webhook_management_deliveries@example.com",
    )
    conversation_id = create_conversation(
        client,
        owner,
        "webhook_management_deliveries_customer@example.com",
    )
    endpoint = create_endpoint(db_session, owner["organization_id"])

    pending = create_delivery(
        db_session,
        owner["organization_id"],
        endpoint.id,
        conversation_id,
        delivery_status="pending",
    )
    create_delivery(
        db_session,
        owner["organization_id"],
        endpoint.id,
        conversation_id,
        delivery_status="failed",
        attempt_count=2,
    )

    response = client.get(
        f"/api/v1/webhooks/{endpoint.id}/deliveries",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert len(response.json()) == 2

    pending_response = client.get(
        f"/api/v1/webhooks/{endpoint.id}/deliveries",
        headers=auth_headers(owner),
        params={"status": "pending"},
    )

    assert pending_response.status_code == 200
    assert len(pending_response.json()) == 1
    assert pending_response.json()[0]["id"] == str(pending.id)


def test_list_webhook_deliveries_pagination(client, db_session):
    owner = register_owner(
        client,
        "webhook_management_pagination@example.com",
    )
    conversation_id = create_conversation(
        client,
        owner,
        "webhook_management_pagination_customer@example.com",
    )
    endpoint = create_endpoint(db_session, owner["organization_id"])

    create_delivery(
        db_session,
        owner["organization_id"],
        endpoint.id,
        conversation_id,
    )
    create_delivery(
        db_session,
        owner["organization_id"],
        endpoint.id,
        conversation_id,
    )

    response = client.get(
        f"/api/v1/webhooks/{endpoint.id}/deliveries",
        headers=auth_headers(owner),
        params={"skip": 0, "limit": 1},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_list_webhook_deliveries_rejects_invalid_status(
    client,
    db_session,
):
    owner = register_owner(
        client,
        "webhook_management_invalid_status@example.com",
    )
    endpoint = create_endpoint(db_session, owner["organization_id"])

    response = client.get(
        f"/api/v1/webhooks/{endpoint.id}/deliveries",
        headers=auth_headers(owner),
        params={"status": "unknown"},
    )

    assert response.status_code == 422


def test_list_webhook_deliveries_rejects_other_organization(
    client,
    db_session,
):
    owner_one = register_owner(
        client,
        "webhook_management_delivery_owner_one@example.com",
    )
    owner_two = register_owner(
        client,
        "webhook_management_delivery_owner_two@example.com",
    )
    endpoint = create_endpoint(db_session, owner_two["organization_id"])

    response = client.get(
        f"/api/v1/webhooks/{endpoint.id}/deliveries",
        headers=auth_headers(owner_one),
    )

    assert response.status_code == 404


def test_manual_retry_resets_failed_delivery(
    client,
    db_session,
):
    owner = register_owner(
        client,
        "webhook_management_retry@example.com",
    )
    conversation_id = create_conversation(
        client,
        owner,
        "webhook_management_retry_customer@example.com",
    )
    endpoint = create_endpoint(db_session, owner["organization_id"])

    delivery = create_delivery(
        db_session,
        owner["organization_id"],
        endpoint.id,
        conversation_id,
        delivery_status="failed",
        attempt_count=3,
    )
    delivery_id = delivery.id

    response = client.post(
        f"/api/v1/webhooks/deliveries/{delivery_id}/retry",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Webhook delivery queued for retry"

    db_session.refresh(delivery)

    assert delivery.status == "pending"
    assert delivery.attempt_count == 0
    assert delivery.next_attempt_at is not None
    assert delivery.last_attempt_at is None
    assert delivery.response_status is None
    assert delivery.response_body is None
    assert delivery.last_error is None
    assert delivery.delivered_at is None


def test_manual_retry_rejects_non_failed_delivery(
    client,
    db_session,
):
    owner = register_owner(
        client,
        "webhook_management_retry_pending@example.com",
    )
    conversation_id = create_conversation(
        client,
        owner,
        "webhook_management_retry_pending_customer@example.com",
    )
    endpoint = create_endpoint(db_session, owner["organization_id"])

    delivery = create_delivery(
        db_session,
        owner["organization_id"],
        endpoint.id,
        conversation_id,
        delivery_status="pending",
    )

    response = client.post(
        f"/api/v1/webhooks/deliveries/{delivery.id}/retry",
        headers=auth_headers(owner),
    )

    assert response.status_code == 409


def test_manual_retry_rejects_other_organization(
    client,
    db_session,
):
    owner_one = register_owner(
        client,
        "webhook_management_retry_owner_one@example.com",
    )
    owner_two = register_owner(
        client,
        "webhook_management_retry_owner_two@example.com",
    )
    conversation_id = create_conversation(
        client,
        owner_two,
        "webhook_management_retry_owner_two_customer@example.com",
    )
    endpoint = create_endpoint(db_session, owner_two["organization_id"])

    delivery = create_delivery(
        db_session,
        owner_two["organization_id"],
        endpoint.id,
        conversation_id,
        delivery_status="failed",
        attempt_count=2,
    )

    response = client.post(
        f"/api/v1/webhooks/deliveries/{delivery.id}/retry",
        headers=auth_headers(owner_one),
    )

    assert response.status_code == 404
