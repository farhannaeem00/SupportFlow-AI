
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WidgetConfigResponse(BaseModel):
    organization_name: str


class WidgetSessionResponse(BaseModel):
    session_token: str
    expires_at: datetime


class WidgetConversationCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    email: str | None = Field(default=None, max_length=255)
    subject: str = Field(
        default="Website support request",
        min_length=1,
        max_length=200,
    )
    message: str = Field(min_length=1, max_length=10000)


class WidgetMessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=10000)


class WidgetMessageResponse(BaseModel):
    id: UUID
    sender_type: str
    content: str
    message_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WidgetConversationResponse(BaseModel):
    id: UUID
    subject: str
    status: str
    created_at: datetime
    messages: list[WidgetMessageResponse]

    model_config = ConfigDict(from_attributes=True)
