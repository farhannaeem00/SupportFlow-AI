from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WebhookEndpointCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    url: str = Field(min_length=1, max_length=2048)
    subscribed_events: list[str] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Webhook name must contain at least 2 characters")
        return value

    @field_validator("subscribed_events")
    @classmethod
    def validate_events(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("At least one event subscription is required")
        if len(value) != len(set(value)):
            raise ValueError("Duplicate event subscriptions are not allowed")
        return value


class WebhookEndpointUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    subscribed_events: list[str] | None = Field(default=None, min_length=1)
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Webhook name must contain at least 2 characters")
        return value

    @field_validator("subscribed_events")
    @classmethod
    def validate_events(
        cls,
        value: list[str] | None,
    ) -> list[str] | None:
        if value is None:
            return value
        if not value:
            raise ValueError("At least one event subscription is required")
        if len(value) != len(set(value)):
            raise ValueError("Duplicate event subscriptions are not allowed")
        return value


class WebhookEndpointResponse(BaseModel):
    id: UUID
    organization_id: UUID
    created_by_id: UUID | None
    name: str
    url: str
    subscribed_events: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WebhookEndpointCreatedResponse(BaseModel):
    endpoint: WebhookEndpointResponse
    signing_secret: str


class WebhookSecretRotationResponse(BaseModel):
    endpoint_id: UUID
    signing_secret: str


class WebhookDeliveryResponse(BaseModel):
    id: UUID
    endpoint_id: UUID
    event_id: UUID
    event_type: str
    payload: dict
    status: str
    attempt_count: int
    max_attempts: int
    next_attempt_at: datetime | None
    last_attempt_at: datetime | None
    response_status: int | None
    response_body: str | None
    last_error: str | None
    delivered_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WebhookMessageResponse(BaseModel):
    message: str