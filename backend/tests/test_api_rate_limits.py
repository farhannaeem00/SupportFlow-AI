from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.config import settings
from app.services.auth_rate_limit_service import (
    enforce_ai_analysis_rate_limit,
)


def test_global_api_rate_limit_returns_429_and_retry_after(
    client,
    monkeypatch,
):
    monkeypatch.setattr(settings, "api_global_rate_limit", 1)

    first_response = client.get("/api/v1/auth/me")
    second_response = client.get("/api/v1/auth/me")

    # The route requires authentication, but the global limiter
    # must allow the first request through to authentication.
    assert first_response.status_code == 401

    assert second_response.status_code == 429
    assert second_response.json()["detail"] == (
        "API request limit exceeded. Please try again later."
    )
    assert int(second_response.headers["Retry-After"]) >= 1


def test_health_routes_are_excluded_from_global_rate_limit(
    client,
    monkeypatch,
):
    monkeypatch.setattr(settings, "api_global_rate_limit", 1)

    root_first = client.get("/")
    root_second = client.get("/")

    health_first = client.get("/health")
    health_second = client.get("/health")

    database_health_first = client.get("/health/database")
    database_health_second = client.get("/health/database")

    assert root_first.status_code == 200
    assert root_second.status_code == 200
    assert health_first.status_code == 200
    assert health_second.status_code == 200
    assert database_health_first.status_code == 200
    assert database_health_second.status_code == 200


def test_ai_analysis_rate_limit_returns_429_and_retry_after(
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(settings, "ai_analysis_rate_limit", 1)

    organization_id = str(uuid4())
    user_id = str(uuid4())

    enforce_ai_analysis_rate_limit(
        db=db_session,
        organization_id=organization_id,
        user_id=user_id,
    )

    with pytest.raises(HTTPException) as exc_info:
        enforce_ai_analysis_rate_limit(
            db=db_session,
            organization_id=organization_id,
            user_id=user_id,
        )

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == (
        "AI analysis limit exceeded. Please try again later."
    )
    assert int(exc_info.value.headers["Retry-After"]) >= 1


def test_ai_analysis_rate_limit_isolated_by_organization_and_user(
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(settings, "ai_analysis_rate_limit", 1)

    organization_a = str(uuid4())
    organization_b = str(uuid4())
    user_a = str(uuid4())
    user_b = str(uuid4())

    # First user in first organization.
    enforce_ai_analysis_rate_limit(
        db=db_session,
        organization_id=organization_a,
        user_id=user_a,
    )

    # A different user in the same organization has a separate quota.
    enforce_ai_analysis_rate_limit(
        db=db_session,
        organization_id=organization_a,
        user_id=user_b,
    )

    # The same user in another organization has a separate quota.
    enforce_ai_analysis_rate_limit(
        db=db_session,
        organization_id=organization_b,
        user_id=user_a,
    )
