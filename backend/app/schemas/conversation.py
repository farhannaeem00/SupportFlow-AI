import uuid

from datetime import datetime
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)
from app.schemas.customer import CustomerResponse



class ConversationCreate(BaseModel):
    customer_id: uuid.UUID
    subject: str = Field(min_length=1, max_length=200)
    priority: str = "normal"
    channel: str = "web_widget"

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Subject cannot be empty")
        return value
    


class ConversationResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    customer_id: uuid.UUID
    assigned_to_id: uuid.UUID | None
    subject: str
    status: str
    priority: str
    channel: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)



class ConversationDetailResponse(ConversationResponse):
    customer: CustomerResponse


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_type: str
    sender_user_id: uuid.UUID | None
    sender_customer_id: uuid.UUID | None
    content: str
    message_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=10000)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be empty")
        return value

class ConversationAssignmentUpdate(BaseModel):
    assigned_to_id: uuid.UUID | None


class ConversationStatusUpdate(BaseModel):
    status: str = Field(
        pattern="^(open|pending|resolved|closed)$"
    )


class ConversationPriorityUpdate(BaseModel):
    priority: str = Field(
        pattern="^(low|normal|high|urgent)$"
    )
class ConversationEventResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    actor_id: uuid.UUID | None
    event_type: str
    old_value: str | None
    new_value: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)