import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.conversation_event import ConversationEvent
from app.models.webhook import WebhookDelivery, WebhookEndpoint


WEBHOOK_EVENT_TYPES = {
    "conversation_created": "conversation.created",
    "message_created": "message.created",
    "assignment_changed": "conversation.assigned",
    "status_changed": "conversation.status_changed",
    "priority_changed": "conversation.priority_changed",
}


class UnsupportedWebhookEventError(ValueError):
    """Raised when an event has no registered public webhook equivalent."""


class WebhookEventValidationError(ValueError):
    """Raised when an event does not belong to the supplied organization."""


def enqueue_webhook_deliveries(
    db: Session,
    organization_id: uuid.UUID,
    event: ConversationEvent,
    extra_data: dict[str, Any] | None = None,
) -> list[WebhookDelivery]:
    """
    Enqueue deliveries for active subscriptions matching this event.

    This function participates in the caller's transaction and never commits.
    """
    public_event_type = WEBHOOK_EVENT_TYPES.get(event.event_type)

    if public_event_type is None:
        raise UnsupportedWebhookEventError(
            f"Unsupported webhook event type: {event.event_type}"
        )

    if not isinstance(organization_id, uuid.UUID):
        raise ValueError("A valid organization UUID is required.")

    if extra_data is not None and not isinstance(extra_data, dict):
        raise ValueError("Webhook event extra_data must be a dictionary.")

    if not event.conversation_id:
        raise ValueError("Conversation ID is required.")

    # Enforce tenant ownership independently of the calling service.
    conversation_belongs_to_organization = db.scalar(
        select(Conversation.id).where(
            Conversation.id == event.conversation_id,
            Conversation.organization_id == organization_id,
        )
    )

    if conversation_belongs_to_organization is None:
        raise WebhookEventValidationError(
            "The conversation does not belong to the supplied organization."
        )

    db.add(event)
    db.flush()

    endpoints = db.scalars(
        select(WebhookEndpoint).where(
            WebhookEndpoint.organization_id == organization_id,
            WebhookEndpoint.is_active.is_(True),
        )
    ).all()

    matching_endpoints = [
        endpoint
        for endpoint in endpoints
        if isinstance(endpoint.subscribed_events, list)
        and public_event_type in endpoint.subscribed_events
    ]

    if not matching_endpoints:
        return []

    created_at = event.created_at or datetime.now(timezone.utc)

    payload = {
        "event_id": str(event.id),
        "event_type": public_event_type,
        "created_at": created_at.isoformat(),
        "organization_id": str(organization_id),
        "data": {
            **(extra_data or {}),
            "conversation_id": str(event.conversation_id),
            "actor_id": str(event.actor_id) if event.actor_id else None,
            "old_value": event.old_value,
            "new_value": event.new_value,
},
        
    }

    now = datetime.now(timezone.utc)

    deliveries = [
        WebhookDelivery(
            organization_id=organization_id,
            endpoint_id=endpoint.id,
            event_id=event.id,
            event_type=public_event_type,
            payload=payload.copy(),
            status="pending",
            attempt_count=0,
            max_attempts=5,
            next_attempt_at=now,
        )
        for endpoint in matching_endpoints
    ]

    db.add_all(deliveries)
    db.flush()

    return deliveries