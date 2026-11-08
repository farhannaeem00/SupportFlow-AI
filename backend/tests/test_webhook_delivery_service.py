import hashlib
import hmac
import json
import uuid
from datetime import timedelta
from urllib.parse import parse_qs

import httpx
import pytest
from cryptography.fernet import Fernet
from sqlalchemy.orm import sessionmaker

from app.models.conversation_event import ConversationEvent
from app.models.webhook import WebhookDelivery, WebhookEndpoint
from app.services import webhook_delivery_service as delivery_service
from app.services.webhook_event_service import enqueue_webhook_deliveries
from app.services.webhook_security import encrypt_signing_secret


TEST_SECRET = "test-webhook-signing-secret"


@pytest.fixture
def delivery_db(db_session, monkeypatch):
    """Keep service-created sessions inside the test's rollback transaction."""
    connection = db_session.connection()

    test_session_factory = sessionmaker(
        bind=connection,
        autoflush=False,
        autocommit=False,
        join_transaction_mode="create_savepoint",
    )

    monkeypatch.setattr(
        delivery_service,
        "SessionLocal",
        test_session_factory,
    )

    return db_session


@pytest.fixture
def webhook_encryption_key(monkeypatch):
    from app.services import webhook_security

    key = Fernet.generate_key().decode("ascii")

    monkeypatch.setattr(
        webhook_security.settings,
        "webhook_encryption_key",
        key,
    )

    return key


def register_owner(client, email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Webhook Delivery Owner",
            "email": email,
            "password": "OwnerPassword123!",
            "organization_name": "Webhook Delivery Organization",
        },
    )

    assert response.status_code == 201
    data = response.json()

    return {
        "token": data["access_token"],
        "organization_id": uuid.UUID(data["organization"]["id"]),
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
            "full_name": "Webhook Delivery Customer",
            "email": email,
            "phone": "03001234567",
            "company": "Delivery Test Company",
        },
    )

    assert customer_response.status_code == 201

    conversation_response = client.post(
        "/api/v1/conversations",
        headers=headers,
        json={
            "customer_id": customer_response.json()["id"],
            "subject": "Webhook delivery test",
            "priority": "normal",
            "channel": "web_widget",
        },
    )

    assert conversation_response.status_code == 201

    return uuid.UUID(conversation_response.json()["id"])


def create_delivery(client, db_session, email):
    owner = register_owner(client, email)
    conversation_id = create_conversation(
        client,
        owner,
        f"customer_{email}",
    )

    endpoint = WebhookEndpoint(
        organization_id=owner["organization_id"],
        name="Delivery Test Endpoint",
        url="https://hooks.example.com/supportflow",
        encrypted_secret=encrypt_signing_secret(TEST_SECRET),
        subscribed_events=["conversation.status_changed"],
        is_active=True,
    )
    db_session.add(endpoint)
    db_session.flush()

    event = ConversationEvent(
        conversation_id=conversation_id,
        event_type="status_changed",
        old_value="open",
        new_value="pending",
    )

    deliveries = enqueue_webhook_deliveries(
        db_session,
        owner["organization_id"],
        event,
    )

    assert len(deliveries) == 1

    return deliveries[0]


class FakeResponse:
    def __init__(self, status_code=200, text="accepted"):
        self.status_code = status_code
        self.text = text


class FakeClient:
    def __init__(self, *, response=None, error=None, calls=None, **kwargs):
        self.response = response or FakeResponse()
        self.error = error
        self.calls = calls if calls is not None else []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def post(self, url, *, content, headers):
        self.calls.append(
            {
                "url": url,
                "content": content,
                "headers": headers,
            }
        )

        if self.error:
            raise self.error

        return self.response


@pytest.fixture
def allow_test_webhook_url(monkeypatch):
    monkeypatch.setattr(
        delivery_service,
        "validate_webhook_url",
        lambda url: url,
    )


def install_fake_client(monkeypatch, *, response=None, error=None):
    calls = []

    def fake_client_factory(**kwargs):
        assert kwargs["follow_redirects"] is False
        assert kwargs["trust_env"] is False

        return FakeClient(
            response=response,
            error=error,
            calls=calls,
            **kwargs,
        )

    monkeypatch.setattr(
        delivery_service.httpx,
        "Client",
        fake_client_factory,
    )

    return calls


def test_successful_delivery_sends_signed_request(
    client,
    db_session,
    delivery_db,
    webhook_encryption_key,
    allow_test_webhook_url,
    monkeypatch,
):
    delivery = create_delivery(
        client,
        db_session,
        "delivery_success@example.com",
    )

    calls = install_fake_client(
        monkeypatch,
        response=FakeResponse(200, "received"),
    )

    result = delivery_service.deliver_webhook(delivery.id)

    assert result is True
    assert len(calls) == 1

    request = calls[0]
    headers = request["headers"]

    assert request["url"] == "https://hooks.example.com/supportflow"
    assert headers["Content-Type"] == "application/json"
    assert headers["X-SupportFlow-Event"] == "conversation.status_changed"
    assert headers["X-SupportFlow-Delivery"] == str(delivery.id)
    assert headers["X-SupportFlow-Event-ID"] == str(delivery.event_id)

    timestamp = headers["X-SupportFlow-Timestamp"]
    signature = headers["X-SupportFlow-Signature"]

    expected_digest = hmac.new(
        TEST_SECRET.encode("utf-8"),
        timestamp.encode("utf-8") + b"." + request["content"],
        hashlib.sha256,
    ).hexdigest()

    assert signature == f"t={timestamp},v1={expected_digest}"

    payload = json.loads(request["content"])
    assert payload["event_type"] == "conversation.status_changed"

    db_session.expire_all()

    stored = db_session.get(WebhookDelivery, delivery.id)

    assert stored.status == "delivered"
    assert stored.attempt_count == 1
    assert stored.response_status == 200
    assert stored.response_body == "received"
    assert stored.delivered_at is not None
    assert stored.next_attempt_at is None


def test_server_error_schedules_retry(
    client,
    db_session,
    delivery_db,
    webhook_encryption_key,
    allow_test_webhook_url,
    monkeypatch,
):
    delivery = create_delivery(
        client,
        db_session,
        "delivery_retry@example.com",
    )

    install_fake_client(
        monkeypatch,
        response=FakeResponse(503, "temporarily unavailable"),
    )

    result = delivery_service.deliver_webhook(delivery.id)

    assert result is False

    db_session.expire_all()

    stored = db_session.get(WebhookDelivery, delivery.id)

    assert stored.status == "retrying"
    assert stored.attempt_count == 1
    assert stored.response_status == 503
    assert stored.last_error is not None
    assert stored.next_attempt_at is not None
    assert stored.next_attempt_at > delivery_service._utc_now()


def test_client_error_marks_delivery_failed(
    client,
    db_session,
    delivery_db,
    webhook_encryption_key,
    allow_test_webhook_url,
    monkeypatch,
):
    delivery = create_delivery(
        client,
        db_session,
        "delivery_client_error@example.com",
    )

    install_fake_client(
        monkeypatch,
        response=FakeResponse(400, "invalid payload"),
    )

    result = delivery_service.deliver_webhook(delivery.id)

    assert result is False

    db_session.expire_all()

    stored = db_session.get(WebhookDelivery, delivery.id)

    assert stored.status == "failed"
    assert stored.attempt_count == 1
    assert stored.response_status == 400
    assert stored.next_attempt_at is None


def test_transport_error_schedules_retry(
    client,
    db_session,
    delivery_db,
    webhook_encryption_key,
    allow_test_webhook_url,
    monkeypatch,
):
    delivery = create_delivery(
        client,
        db_session,
        "delivery_transport_error@example.com",
    )

    request = httpx.Request(
        "POST",
        "https://hooks.example.com/supportflow",
    )

    install_fake_client(
        monkeypatch,
        error=httpx.ConnectError("Connection refused", request=request),
    )

    result = delivery_service.deliver_webhook(delivery.id)

    assert result is False

    db_session.expire_all()

    stored = db_session.get(WebhookDelivery, delivery.id)

    assert stored.status == "retrying"
    assert stored.attempt_count == 1
    assert "transport error" in stored.last_error.lower()
    assert stored.next_attempt_at is not None


def test_delivery_cannot_be_claimed_twice_while_processing(
    client,
    db_session,
    delivery_db,
    webhook_encryption_key,
):
    delivery = create_delivery(
        client,
        db_session,
        "delivery_claim@example.com",
    )

    first_claim = delivery_service._claim_delivery(delivery.id)

    assert first_claim is not None

    second_claim = delivery_service._claim_delivery(delivery.id)

    assert second_claim is None

    db_session.expire_all()

    stored = db_session.get(WebhookDelivery, delivery.id)

    assert stored.status == "processing"
    assert stored.attempt_count == 1


def test_delivery_with_exhausted_attempts_is_not_claimed(
    client,
    db_session,
    delivery_db,
    webhook_encryption_key,
):
    delivery = create_delivery(
        client,
        db_session,
        "delivery_exhausted@example.com",
    )

    delivery.status = "retrying"
    delivery.attempt_count = delivery.max_attempts
    delivery.next_attempt_at = None
    db_session.flush()

    snapshot = delivery_service._claim_delivery(delivery.id)

    assert snapshot is None

    db_session.expire_all()

    stored = db_session.get(WebhookDelivery, delivery.id)

    assert stored.status == "failed"
    assert stored.attempt_count == stored.max_attempts
    assert stored.next_attempt_at is None


def test_inactive_endpoint_marks_delivery_failed(
    client,
    db_session,
    delivery_db,
    webhook_encryption_key,
):
    delivery = create_delivery(
        client,
        db_session,
        "delivery_inactive@example.com",
    )

    endpoint = db_session.get(WebhookEndpoint, delivery.endpoint_id)
    endpoint.is_active = False
    db_session.flush()

    snapshot = delivery_service._claim_delivery(delivery.id)

    assert snapshot is None

    db_session.expire_all()

    stored = db_session.get(WebhookDelivery, delivery.id)

    assert stored.status == "failed"
    assert "inactive" in stored.last_error.lower()


def test_old_worker_cannot_overwrite_newer_claim(
    client,
    db_session,
    delivery_db,
    webhook_encryption_key,
):
    delivery = create_delivery(
        client,
        db_session,
        "delivery_stale_worker@example.com",
    )

    old_snapshot = delivery_service._claim_delivery(delivery.id)

    assert old_snapshot is not None

    # Simulate a worker whose processing lease expired.
    endpoint_delivery = db_session.get(WebhookDelivery, delivery.id)
    endpoint_delivery.last_attempt_at = (
        delivery_service._utc_now() - timedelta(minutes=10)
    )
    db_session.flush()

    newer_snapshot = delivery_service._claim_delivery(delivery.id)

    assert newer_snapshot is not None
    assert newer_snapshot.claimed_at != old_snapshot.claimed_at

    delivery_service._finish_delivery(
        old_snapshot,
        status="delivered",
        response_status=200,
    )

    db_session.expire_all()

    stored = db_session.get(WebhookDelivery, delivery.id)

    assert stored.status == "processing"
    assert stored.attempt_count == 2
    assert stored.last_attempt_at == newer_snapshot.claimed_at


@pytest.mark.parametrize(
    ("attempt", "expected"),
    [
        (1, 30),
        (2, 60),
        (3, 120),
        (4, 240),
        (5, 480),
        (10, 3600),
        (20, 3600),
    ],
)
def test_retry_delay_uses_capped_exponential_backoff(attempt, expected):
    assert delivery_service._retry_delay_seconds(attempt) == expected


def test_process_due_deliveries_processes_pending_delivery(
    client,
    db_session,
    delivery_db,
    webhook_encryption_key,
    allow_test_webhook_url,
    monkeypatch,
):
    delivery = create_delivery(
        client,
        db_session,
        "delivery_worker@example.com",
    )

    install_fake_client(
        monkeypatch,
        response=FakeResponse(204, ""),
    )

    result = delivery_service.process_due_webhook_deliveries(limit=10)

    assert result["selected"] >= 1
    assert result["attempted"] == 1
    assert result["delivered"] == 1
    assert result["failed_or_retrying"] == 0

    db_session.expire_all()

    stored = db_session.get(WebhookDelivery, delivery.id)

    assert stored.status == "delivered"