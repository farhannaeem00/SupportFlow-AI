
import hashlib
import hmac
import math
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AuthRateLimit

from fastapi import Depends, HTTPException, Request, status
from app.database import get_db

def _hash_client_key(client_key: str) -> str:
    return hmac.new(
        settings.jwt_secret_key.encode("utf-8"),
        client_key.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def enforce_auth_rate_limit(
    db: Session,
    client_key: str,
    action: str,
    limit: int,
) -> None:
    now = datetime.now(timezone.utc)
    window_seconds = settings.auth_rate_limit_window_seconds

    window_timestamp = (
        math.floor(now.timestamp() / window_seconds)
        * window_seconds
    )

    window_start = datetime.fromtimestamp(
        window_timestamp,
        tz=timezone.utc,
    )

    statement = insert(AuthRateLimit).values(
        client_key_hash=_hash_client_key(client_key),
        action=action,
        window_start=window_start,
        request_count=1,
        created_at=now,
        updated_at=now,
    )

    statement = statement.on_conflict_do_update(
        constraint="uq_auth_rate_limit_window",
        set_={
            "request_count": AuthRateLimit.request_count + 1,
            "updated_at": now,
        },
    ).returning(AuthRateLimit.request_count)

    request_count = db.execute(statement).scalar_one()
    db.commit()

    if request_count > limit:
        retry_after = max(
            1,
            math.ceil(
                window_seconds - (now.timestamp() - window_timestamp)
            ),
        )

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

def enforce_global_api_rate_limit(
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    client_ip = (
        request.client.host
        if request.client is not None
        else "unknown"
    )

    now = datetime.now(timezone.utc)
    window_seconds = settings.api_rate_limit_window_seconds

    window_timestamp = (
        math.floor(now.timestamp() / window_seconds)
        * window_seconds
    )

    window_start = datetime.fromtimestamp(
        window_timestamp,
        tz=timezone.utc,
    )

    statement = insert(AuthRateLimit).values(
        client_key_hash=_hash_client_key(client_ip),
        action="api_global",
        window_start=window_start,
        request_count=1,
        created_at=now,
        updated_at=now,
    )

    statement = statement.on_conflict_do_update(
        constraint="uq_auth_rate_limit_window",
        set_={
            "request_count": AuthRateLimit.request_count + 1,
            "updated_at": now,
        },
    ).returning(AuthRateLimit.request_count)

    request_count = db.execute(statement).scalar_one()
    db.commit()

    if request_count > settings.api_global_rate_limit:
        retry_after = max(
            1,
            math.ceil(
                window_seconds - (now.timestamp() - window_timestamp)
            ),
        )

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="API request limit exceeded. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )
    
def enforce_ai_analysis_rate_limit(
    db: Session,
    organization_id: str,
    user_id: str,
) -> None:
    client_key = f"ai_analysis:{organization_id}:{user_id}"

    now = datetime.now(timezone.utc)
    window_seconds = settings.ai_analysis_rate_limit_window_seconds

    window_timestamp = (
        math.floor(now.timestamp() / window_seconds)
        * window_seconds
    )

    window_start = datetime.fromtimestamp(
        window_timestamp,
        tz=timezone.utc,
    )

    statement = insert(AuthRateLimit).values(
        client_key_hash=_hash_client_key(client_key),
        action="ai_analysis",
        window_start=window_start,
        request_count=1,
        created_at=now,
        updated_at=now,
    )

    statement = statement.on_conflict_do_update(
        constraint="uq_auth_rate_limit_window",
        set_={
            "request_count": AuthRateLimit.request_count + 1,
            "updated_at": now,
        },
    ).returning(AuthRateLimit.request_count)

    request_count = db.execute(statement).scalar_one()
    db.commit()

    if request_count > settings.ai_analysis_rate_limit:
        retry_after = max(
            1,
            math.ceil(
                window_seconds - (now.timestamp() - window_timestamp)
            ),
        )

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI analysis limit exceeded. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )