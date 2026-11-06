import uuid

import pytest
from sqlalchemy import select

from app.models.conversation_event import ConversationEvent
from app.models.webhook import WebhookDelivery, WebhookEndpoint
from app.services.webhook_event_service import (
    UnsupportedWebhookEventError,
    WebhookEventValidationError,
    enqueue_webhook_deliveries,
)


def register_owner(client, email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Webhook Test Owner",
            "email": email,
            "password": "OwnerPassword123!",
            "organization_name": "Webhook Test Organization",
        },
    )
    assert response.status_code == 201
    data = response.json()

    return {
        "token": data["access_token"],
        "organization_id": uuid.UUID(data["organization"]["id"]),
        "user_id": uuid.UUID(data["user"]["id"]),
    }


def create_conversation(client, owner, email):
    headers = {
        "Authorization": f"Bearer {owner['token']}",
        "X-Organization-ID": str(owner["organization_id"]),
    }

    customer_response = client.post(
        "/api/v1/customers",
        headers=headers,
        json={
            "full_name": "Webhook Customer",
            "email": email,
            "phone": "03001234567",
            "company": "Webhook Test Company",
        },
    )
    assert customer_response.status_code == 201

    conversation_response = client.post(
        "/api/v1/conversations",
        headers=headers,
        json={
            "customer_id": customer_response.json()["id"],
            "subject": "Webhook test conversation",
            "priority": "normal",
            "channel": "web_widget",
        },
    )
    assert conversation_response.status_code == 201

    return uuid.UUID(conversation_response.json()["id"])


def create_endpoint(
    db_session,
    organization_id,
    subscribed_events,
    *,
    is_active=True,
):
    endpoint = WebhookEndpoint(
        organization_id=organization_id,
        name="Test Webhook",
        url="https://hooks.example.com/supportflow",
        encrypted_secret="test-encrypted-secret",
        subscribed_events=subscribed_events,
        is_active=is_active,
    )
    db_session.add(endpoint)
    db_session.flush()
    return endpoint


def create_event(conversation_id, event_type="status_changed"):
    return ConversationEvent(
        conversation_id=conversation_id,
        event_type=event_type,
        old_value="open",
        new_value="pending",
    )


def test_matching_subscription_creates_delivery(client, db_session):
    owner = register_owner(client, "webhook_event_one@example.com")
    conversation_id = create_conversation(
        client, owner, "webhook_customer_one@example.com"
    )

    endpoint = create_endpoint(
        db_session,
        owner["organization_id"],
        ["conversation.status_changed"],
    )

    event = create_event(conversation_id)

    deliveries = enqueue_webhook_deliveries(
        db_session,
        owner["organization_id"],
        event,
    )

    assert len(deliveries) == 1

    delivery = deliveries[0]

    assert delivery.endpoint_id == endpoint.id
    assert delivery.event_id == event.id
    assert delivery.organization_id == owner["organization_id"]
    assert delivery.event_type == "conversation.status_changed"
    assert delivery.status == "pending"
    assert delivery.attempt_count == 0
    assert delivery.max_attempts == 5
    assert delivery.next_attempt_at is not None

    assert delivery.payload["event_id"] == str(event.id)
    assert delivery.payload["event_type"] == "conversation.status_changed"
    assert delivery.payload["organization_id"] == str(
        owner["organization_id"]
    )
    assert delivery.payload["data"]["conversation_id"] == str(
        conversation_id
    )


def test_multiple_matching_endpoints_each_receive_delivery(
    client,
    db_session,
):
    owner = register_owner(client, "webhook_event_two@example.com")
    conversation_id = create_conversation(
        client, owner, "webhook_customer_two@example.com"
    )

    first = create_endpoint(
        db_session,
        owner["organization_id"],
        ["conversation.status_changed"],
    )
    second = create_endpoint(
        db_session,
        owner["organization_id"],
        ["conversation.status_changed", "conversation.assigned"],
    )

    deliveries = enqueue_webhook_deliveries(
        db_session,
        owner["organization_id"],
        create_event(conversation_id),
    )

    assert len(deliveries) == 2
    assert {delivery.endpoint_id for delivery in deliveries} == {
        first.id,
        second.id,
    }


def test_non_matching_subscription_creates_no_delivery(
    client,
    db_session,
):
    owner = register_owner(client, "webhook_event_three@example.com")
    conversation_id = create_conversation(
        client, owner, "webhook_customer_three@example.com"
    )

    create_endpoint(
        db_session,
        owner["organization_id"],
        ["conversation.assigned"],
    )

    deliveries = enqueue_webhook_deliveries(
        db_session,
        owner["organization_id"],
        create_event(conversation_id, "status_changed"),
    )

    assert deliveries == []


def test_inactive_endpoint_creates_no_delivery(client, db_session):
    owner = register_owner(client, "webhook_event_four@example.com")
    conversation_id = create_conversation(
        client, owner, "webhook_customer_four@example.com"
    )

    create_endpoint(
        db_session,
        owner["organization_id"],
        ["conversation.status_changed"],
        is_active=False,
    )

    deliveries = enqueue_webhook_deliveries(
        db_session,
        owner["organization_id"],
        create_event(conversation_id),
    )

    assert deliveries == []


def test_organization_isolation(client, db_session):
    owner_one = register_owner(client, "webhook_event_five@example.com")
    owner_two = register_owner(client, "webhook_event_six@example.com")

    conversation_id = create_conversation(
        client, owner_one, "webhook_customer_five@example.com"
    )

    create_endpoint(
        db_session,
        owner_two["organization_id"],
        ["conversation.status_changed"],
    )

    deliveries = enqueue_webhook_deliveries(
        db_session,
        owner_one["organization_id"],
        create_event(conversation_id),
    )

    assert deliveries == []


def test_cross_organization_event_is_rejected(client, db_session):
    owner_one = register_owner(client, "webhook_event_seven@example.com")
    owner_two = register_owner(client, "webhook_event_eight@example.com")

    conversation_id = create_conversation(
        client, owner_two, "webhook_customer_eight@example.com"
    )

    event = create_event(conversation_id)

    with pytest.raises(WebhookEventValidationError):
        enqueue_webhook_deliveries(
            db_session,
            owner_one["organization_id"],
            event,
        )

    assert event not in db_session


def test_unsupported_event_type_is_rejected(client, db_session):
    owner = register_owner(client, "webhook_event_nine@example.com")
    conversation_id = create_conversation(
        client, owner, "webhook_customer_nine@example.com"
    )

    event = create_event(conversation_id, "unknown_event")

    with pytest.raises(UnsupportedWebhookEventError):
        enqueue_webhook_deliveries(
            db_session,
            owner["organization_id"],
            event,
        )

    assert event not in db_session


def test_extra_data_is_included_in_payload(client, db_session):
    owner = register_owner(client, "webhook_event_ten@example.com")
    conversation_id = create_conversation(
        client, owner, "webhook_customer_ten@example.com"
    )

    create_endpoint(
        db_session,
        owner["organization_id"],
        ["conversation.status_changed"],
    )

    deliveries = enqueue_webhook_deliveries(
        db_session,
        owner["organization_id"],
        create_event(conversation_id),
        extra_data={"priority": "urgent"},
    )

    assert len(deliveries) == 1
    assert deliveries[0].payload["data"]["priority"] == "urgent"


def test_event_and_delivery_are_flushed_without_committing(
    client,
    db_session,
):
    owner = register_owner(client, "webhook_event_eleven@example.com")
    conversation_id = create_conversation(
        client, owner, "webhook_customer_eleven@example.com"
    )

    create_endpoint(
        db_session,
        owner["organization_id"],
        ["conversation.status_changed"],
    )

    event = create_event(conversation_id)

    deliveries = enqueue_webhook_deliveries(
        db_session,
        owner["organization_id"],
        event,
    )

    assert db_session.in_transaction()
    assert event.id is not None
    assert len(deliveries) == 1

    stored_event = db_session.scalar(
        select(ConversationEvent).where(
            ConversationEvent.id == event.id
        )
    )
    stored_delivery = db_session.scalar(
        select(WebhookDelivery).where(
            WebhookDelivery.id == deliveries[0].id
        )
    )

    assert stored_event is not None
    assert stored_delivery is not None