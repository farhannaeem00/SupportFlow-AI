
import hashlib
import hmac
import math
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models import WidgetRateLimit


def _hash_client_key(client_key: str) -> str:
    """Hash visitor identifiers before storing them."""
    return hmac.new(
        settings.jwt_secret_key.encode("utf-8"),
        client_key.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def enforce_widget_rate_limit(
    db: Session,
    organization_id: UUID,
    client_key: str,
    action: str,
    limit: int,
) -> None:
    """
    Enforce a fixed-window rate limit using an atomic PostgreSQL upsert.

    Raises HTTP 429 when the configured limit is exceeded.
    """

    now = datetime.now(timezone.utc)
    window_seconds = settings.widget_rate_limit_window_seconds

    window_timestamp = (
        math.floor(now.timestamp() / window_seconds)
        * window_seconds
    )

    window_start = datetime.fromtimestamp(
        window_timestamp,
        tz=timezone.utc,
    )

    client_key_hash = _hash_client_key(client_key)

    statement = insert(WidgetRateLimit).values(
        organization_id=organization_id,
        client_key_hash=client_key_hash,
        action=action,
        window_start=window_start,
        request_count=1,
        created_at=now,
        updated_at=now,
    )

    statement = statement.on_conflict_do_update(
        constraint="uq_widget_rate_limit_window",
        set_={
            "request_count": WidgetRateLimit.request_count + 1,
            "updated_at": now,
        },
    ).returning(WidgetRateLimit.request_count)

    request_count = db.execute(statement).scalar_one()

    # Persist the counter, including requests that exceed the limit.
    db.commit()

    if request_count > limit:
        retry_after = max(
            1,
            math.ceil(
                window_seconds
                - (now.timestamp() - window_timestamp)
            ),
        )

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )
