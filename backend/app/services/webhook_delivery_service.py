from __future__ import annotations

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import and_, or_, select

from app.database import SessionLocal
from app.models.webhook import WebhookDelivery, WebhookEndpoint
from app.services.webhook_security import (
    decrypt_signing_secret,
    validate_webhook_url,
)

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = httpx.Timeout(
    connect=5.0,
    read=10.0,
    write=10.0,
    pool=5.0,
)

RETRYABLE_STATUS_CODES = {408, 425, 429}
MAX_RESPONSE_BODY_LENGTH = 2_000
STALE_PROCESSING_AFTER = timedelta(minutes=5)
BASE_RETRY_DELAY_SECONDS = 30
MAX_RETRY_DELAY_SECONDS = 3_600


@dataclass(frozen=True)
class DeliverySnapshot:
    delivery_id: UUID
    endpoint_id: UUID
    event_id: UUID
    event_type: str
    url: str
    encrypted_secret: str
    payload: dict[str, Any]
    attempt_count: int
    max_attempts: int
    claimed_at: datetime


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _retry_delay_seconds(attempt_count: int) -> int:
    """Exponential backoff, capped at one hour."""
    exponent = max(0, attempt_count - 1)
    return min(
        BASE_RETRY_DELAY_SECONDS * (2**exponent),
        MAX_RETRY_DELAY_SECONDS,
    )


def _build_signature(secret: str, timestamp: str, body: bytes) -> str:
    signed_content = timestamp.encode("utf-8") + b"." + body
    digest = hmac.new(
        secret.encode("utf-8"),
        signed_content,
        hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


def _claim_delivery(delivery_id: UUID) -> DeliverySnapshot | None:
    """
    Atomically claim one due delivery.

    The row lock is held only while changing its state. The transaction is
    committed before the HTTP request begins.
    """
    db = SessionLocal()

    try:
        now = _utc_now()

        delivery = db.scalar(
            select(WebhookDelivery)
            .where(WebhookDelivery.id == delivery_id)
            .with_for_update(skip_locked=True)
        )

        if delivery is None:
            db.rollback()
            return None

        is_due = (
            delivery.status in {"pending", "retrying"}
            and (
                delivery.next_attempt_at is None
                or delivery.next_attempt_at <= now
            )
        )

        is_stale = (
            delivery.status == "processing"
            and (
                delivery.last_attempt_at is None
                or delivery.last_attempt_at <= now - STALE_PROCESSING_AFTER
            )
        )

        if not (is_due or is_stale):
            db.rollback()
            return None

        if delivery.attempt_count >= delivery.max_attempts:
            delivery.status = "failed"
            delivery.last_error = "Maximum delivery attempts reached"
            delivery.next_attempt_at = None
            db.commit()
            return None

        endpoint = db.get(WebhookEndpoint, delivery.endpoint_id)

        if endpoint is None or not endpoint.is_active:
            delivery.status = "failed"
            delivery.last_error = "Webhook endpoint is missing or inactive"
            delivery.next_attempt_at = None
            db.commit()
            return None

        claimed_at = now
        delivery.status = "processing"
        delivery.attempt_count += 1
        delivery.last_attempt_at = claimed_at
        delivery.next_attempt_at = None

        snapshot = DeliverySnapshot(
            delivery_id=delivery.id,
            endpoint_id=endpoint.id,
            event_id=delivery.event_id,
            event_type=delivery.event_type,
            url=endpoint.url,
            encrypted_secret=endpoint.encrypted_secret,
            payload=delivery.payload,
            attempt_count=delivery.attempt_count,
            max_attempts=delivery.max_attempts,
            claimed_at=claimed_at,
        )

        db.commit()
        return snapshot

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _finish_delivery(
    snapshot: DeliverySnapshot,
    *,
    status: str,
    response_status: int | None = None,
    response_body: str | None = None,
    error: str | None = None,
    retry: bool = False,
) -> None:
    """Persist an attempt result only if this worker still owns the claim."""
    db = SessionLocal()

    try:
        delivery = db.get(WebhookDelivery, snapshot.delivery_id)

        if delivery is None:
            return

        # A newer worker may have reclaimed this delivery. Do not let an
        # older worker overwrite that newer attempt's state.
        if (
            delivery.status != "processing"
            or delivery.last_attempt_at != snapshot.claimed_at
        ):
            return

        delivery.response_status = response_status
        delivery.response_body = (
            response_body[:MAX_RESPONSE_BODY_LENGTH]
            if response_body is not None
            else None
        )
        delivery.last_error = error

        if status == "delivered":
            delivery.status = "delivered"
            delivery.delivered_at = _utc_now()
            delivery.next_attempt_at = None

        elif retry and delivery.attempt_count < delivery.max_attempts:
            delivery.status = "retrying"
            delivery.next_attempt_at = _utc_now() + timedelta(
                seconds=_retry_delay_seconds(delivery.attempt_count)
            )

        else:
            delivery.status = "failed"
            delivery.next_attempt_at = None

        db.commit()

    except Exception:
        db.rollback()
        logger.exception(
            "Failed to persist webhook delivery result: %s",
            snapshot.delivery_id,
        )
        raise
    finally:
        db.close()


def _send_claimed_delivery(snapshot: DeliverySnapshot) -> bool:
    """
    Send one already-claimed delivery.

    Returns True only when the endpoint accepts the event with a 2xx status.
    """
    try:
        # Revalidate immediately before connecting. This is useful defense
        # in depth, but does not eliminate DNS-rebinding/TOCTOU risks.
        validate_webhook_url(snapshot.url)

        secret = decrypt_signing_secret(snapshot.encrypted_secret)

        body = json.dumps(
            snapshot.payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        timestamp = str(int(_utc_now().timestamp()))
        signature = _build_signature(secret, timestamp, body)

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SupportFlow-Webhooks/1.0",
            "X-SupportFlow-Delivery": str(snapshot.delivery_id),
            "X-SupportFlow-Event": snapshot.event_type,
            "X-SupportFlow-Event-ID": str(snapshot.event_id),
            "X-SupportFlow-Timestamp": timestamp,
            "X-SupportFlow-Signature": signature,
        }

        with httpx.Client(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            response = client.post(
                snapshot.url,
                content=body,
                headers=headers,
            )

        response_text = response.text[:MAX_RESPONSE_BODY_LENGTH]

        if 200 <= response.status_code < 300:
            _finish_delivery(
                snapshot,
                status="delivered",
                response_status=response.status_code,
                response_body=response_text,
            )
            return True

        retryable = (
            response.status_code in RETRYABLE_STATUS_CODES
            or response.status_code >= 500
        )

        _finish_delivery(
            snapshot,
            status="retrying" if retryable else "failed",
            response_status=response.status_code,
            response_body=response_text,
            error=f"Webhook endpoint returned HTTP {response.status_code}",
            retry=retryable,
        )
        return False

    except httpx.TransportError as exc:
        # Includes connection errors, timeouts, and other transport failures.
        _finish_delivery(
            snapshot,
            status="retrying",
            error=f"Webhook transport error: {str(exc)[:1000]}",
            retry=True,
        )
        return False

    except Exception as exc:
        logger.exception(
            "Webhook delivery failed unexpectedly: %s",
            snapshot.delivery_id,
        )
        _finish_delivery(
            snapshot,
            status="failed",
            error=f"Webhook delivery error: {str(exc)[:1000]}",
        )
        return False


def deliver_webhook(delivery_id: UUID) -> bool:
    """Claim and immediately attempt one delivery."""
    snapshot = _claim_delivery(delivery_id)

    if snapshot is None:
        return False

    return _send_claimed_delivery(snapshot)


def process_due_webhook_deliveries(limit: int = 100) -> dict[str, int]:
    """
    Process due pending/retrying deliveries and recover stale processing rows.

    This function is intended to be called by a scheduled worker. FastAPI
    BackgroundTasks alone do not provide durable periodic retry execution.
    """
    if limit < 1:
        raise ValueError("limit must be at least 1")

    now = _utc_now()
    stale_before = now - STALE_PROCESSING_AFTER
    db = SessionLocal()

    try:
        due_query = or_(
            and_(
                WebhookDelivery.status.in_(("pending", "retrying")),
                or_(
                    WebhookDelivery.next_attempt_at.is_(None),
                    WebhookDelivery.next_attempt_at <= now,
                ),
            ),
            and_(
                WebhookDelivery.status == "processing",
                or_(
                    WebhookDelivery.last_attempt_at.is_(None),
                    WebhookDelivery.last_attempt_at <= stale_before,
                ),
            ),
        )

        delivery_ids = list(
            db.scalars(
                select(WebhookDelivery.id)
                .where(due_query)
                .order_by(WebhookDelivery.created_at.asc())
                .limit(limit)
            ).all()
        )
    finally:
        db.close()

    attempted = 0
    delivered = 0
    failed_or_retrying = 0
    skipped = 0

    for delivery_id in delivery_ids:
        snapshot = _claim_delivery(delivery_id)

        if snapshot is None:
            skipped += 1
            continue

        attempted += 1

        if _send_claimed_delivery(snapshot):
            delivered += 1
        else:
            failed_or_retrying += 1

    return {
        "selected": len(delivery_ids),
        "attempted": attempted,
        "delivered": delivered,
        "failed_or_retrying": failed_or_retrying,
        "skipped": skipped,
    }