import uuid

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.customer import CustomerResponse


class ConversationCreate(BaseModel):
    customer_id: uuid.UUID
    subject: str = Field(min_length=1, max_length=200)
    priority: str = "normal"
    channel: str = "web_widget"


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