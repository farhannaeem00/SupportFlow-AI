
from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


class WidgetConfigResponse(BaseModel):
    organization_name: str


class WidgetSessionResponse(BaseModel):
    session_token: str
    expires_at: datetime


class WidgetConversationCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    email: EmailStr | None = None
    subject: str = Field(
        default="Website support request",
        min_length=1,
        max_length=200,
    )
    message: str = Field(min_length=1, max_length=10000)

    @field_validator("full_name", "subject", "message")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty")
        return value


class WidgetMessageCreate(BaseModel):
    message: str = Field(min_length=1, max_length=10000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be empty")
        return value


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
