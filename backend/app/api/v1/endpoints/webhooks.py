from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_roles
from app.models import OrganizationMember
from app.models.webhook import WebhookDelivery, WebhookEndpoint
from app.schemas.webhook import (
    WebhookEndpointCreate,
    WebhookEndpointCreatedResponse,
    WebhookEndpointResponse,
    WebhookEndpointUpdate,
    WebhookSecretRotationResponse,
    WebhookDeliveryResponse,
    WebhookMessageResponse,
)
from app.services.webhook_event_service import WEBHOOK_EVENT_TYPES
from app.services.webhook_security import (
    WebhookSecurityError,
    encrypt_signing_secret,
    generate_signing_secret,
    validate_webhook_url,
)

router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"],
)

ALLOWED_EVENTS = set(WEBHOOK_EVENT_TYPES.values())


def _get_endpoint(
    db: Session,
    organization_id: UUID,
    endpoint_id: UUID,
) -> WebhookEndpoint:
    endpoint = db.scalar(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.organization_id == organization_id,
        )
    )

    if endpoint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook endpoint not found",
        )

    return endpoint


def _validate_subscriptions(events: list[str]) -> None:
    unsupported = sorted(set(events) - ALLOWED_EVENTS)

    if unsupported:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "One or more webhook events are unsupported",
                "unsupported_events": unsupported,
                "allowed_events": sorted(ALLOWED_EVENTS),
            },
        )


def _validate_url(url: str) -> str:
    try:
        return validate_webhook_url(url)
    except WebhookSecurityError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.post(
    "",
    response_model=WebhookEndpointCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_webhook_endpoint(
    payload: WebhookEndpointCreate,
    membership: OrganizationMember = Depends(require_roles("owner")),
    db: Session = Depends(get_db),
):
    _validate_subscriptions(payload.subscribed_events)
    validated_url = _validate_url(payload.url)

    signing_secret = generate_signing_secret()

    try:
        encrypted_secret = encrypt_signing_secret(signing_secret)

        endpoint = WebhookEndpoint(
            organization_id=membership.organization_id,
            created_by_id=membership.user_id,
            name=payload.name,
            url=validated_url,
            encrypted_secret=encrypted_secret,
            subscribed_events=payload.subscribed_events,
            is_active=True,
        )

        db.add(endpoint)
        db.commit()
        db.refresh(endpoint)

        return {
            "endpoint": endpoint,
            "signing_secret": signing_secret,
        }

    except Exception:
        db.rollback()
        raise


@router.get(
    "",
    response_model=list[WebhookEndpointResponse],
)
def list_webhook_endpoints(
    membership: OrganizationMember = Depends(require_roles("owner")),
    db: Session = Depends(get_db),
):
    statement = (
        select(WebhookEndpoint)
        .where(
            WebhookEndpoint.organization_id == membership.organization_id,
        )
        .order_by(
            WebhookEndpoint.created_at.desc(),
            WebhookEndpoint.id.desc(),
        )
    )

    return list(db.scalars(statement).all())


@router.patch(
    "/{endpoint_id}",
    response_model=WebhookEndpointResponse,
)
def update_webhook_endpoint(
    endpoint_id: UUID,
    payload: WebhookEndpointUpdate,
    membership: OrganizationMember = Depends(require_roles("owner")),
    db: Session = Depends(get_db),
):
    endpoint = _get_endpoint(
        db,
        membership.organization_id,
        endpoint_id,
    )

    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update fields provided",
        )

    if any(value is None for value in updates.values()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Update fields cannot be null",
        )

    if "subscribed_events" in updates:
        _validate_subscriptions(updates["subscribed_events"])

    if "url" in updates:
        updates["url"] = _validate_url(updates["url"])

    try:
        for field, value in updates.items():
            setattr(endpoint, field, value)

        db.commit()
        db.refresh(endpoint)

        return endpoint

    except Exception:
        db.rollback()
        raise


@router.delete(
    "/{endpoint_id}",
    response_model=WebhookMessageResponse,
)
def delete_webhook_endpoint(
    endpoint_id: UUID,
    membership: OrganizationMember = Depends(require_roles("owner")),
    db: Session = Depends(get_db),
):
    endpoint = _get_endpoint(
        db,
        membership.organization_id,
        endpoint_id,
    )

    try:
        db.delete(endpoint)
        db.commit()

        return {"message": "Webhook endpoint deleted successfully"}

    except Exception:
        db.rollback()
        raise


@router.post(
    "/{endpoint_id}/rotate-secret",
    response_model=WebhookSecretRotationResponse,
)
def rotate_webhook_secret(
    endpoint_id: UUID,
    membership: OrganizationMember = Depends(require_roles("owner")),
    db: Session = Depends(get_db),
):
    endpoint = _get_endpoint(
        db,
        membership.organization_id,
        endpoint_id,
    )

    try:
        signing_secret = generate_signing_secret()
        endpoint.encrypted_secret = encrypt_signing_secret(signing_secret)

        db.commit()

        return {
            "endpoint_id": endpoint.id,
            "signing_secret": signing_secret,
        }

    except Exception:
        db.rollback()
        raise


@router.get(
    "/{endpoint_id}/deliveries",
    response_model=list[WebhookDeliveryResponse],
)
def list_webhook_deliveries(
    endpoint_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    delivery_status: str | None = Query(
        default=None,
        alias="status",
        max_length=20,
    ),
    membership: OrganizationMember = Depends(require_roles("owner")),
    db: Session = Depends(get_db),
):
    _get_endpoint(db, membership.organization_id, endpoint_id)

    statement = select(WebhookDelivery).where(
        WebhookDelivery.organization_id == membership.organization_id,
        WebhookDelivery.endpoint_id == endpoint_id,
    )

    if delivery_status:
        allowed_statuses = {
            "pending",
            "processing",
            "retrying",
            "delivered",
            "failed",
        }

        if delivery_status not in allowed_statuses:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid delivery status filter",
            )

        statement = statement.where(
            WebhookDelivery.status == delivery_status,
        )

    statement = (
        statement
        .order_by(
            WebhookDelivery.created_at.desc(),
            WebhookDelivery.id.desc(),
        )
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


@router.post(
    "/deliveries/{delivery_id}/retry",
    response_model=WebhookMessageResponse,
)
def retry_webhook_delivery(
    delivery_id: UUID,
    membership: OrganizationMember = Depends(require_roles("owner")),
    db: Session = Depends(get_db),
):
    delivery = db.scalar(
        select(WebhookDelivery)
        .where(
            WebhookDelivery.id == delivery_id,
            WebhookDelivery.organization_id == membership.organization_id,
        )
        .with_for_update()
    )

    if delivery is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook delivery not found",
        )

    if delivery.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed deliveries can be manually retried",
        )

    try:
        delivery.status = "pending"
        delivery.attempt_count = 0
        delivery.next_attempt_at = datetime.now(timezone.utc)
        delivery.last_attempt_at = None
        delivery.response_status = None
        delivery.response_body = None
        delivery.last_error = None
        delivery.delivered_at = None

        db.commit()

        return {"message": "Webhook delivery queued for retry"}

    except Exception:
        db.rollback()
        raise