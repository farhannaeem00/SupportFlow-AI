import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.conversation import Conversation
from app.models.organization_member import OrganizationMember
from app.schemas.conversation import ConversationCreate

from sqlalchemy.orm import Session, joinedload

from app.models.message import Message

VALID_PRIORITIES = {"low", "normal", "high", "urgent"}
VALID_CHANNELS = {"web_widget"}


def create_conversation(
    db: Session,
    organization_id: uuid.UUID,
    payload: ConversationCreate,
) -> Conversation:
    if payload.priority not in VALID_PRIORITIES:
        raise ValueError("Invalid conversation priority.")

    if payload.channel not in VALID_CHANNELS:
        raise ValueError("Invalid conversation channel.")

    customer = db.scalar(
        select(Customer).where(
            Customer.id == payload.customer_id,
            Customer.organization_id == organization_id,
            Customer.is_active.is_(True),
        )
    )

    if not customer:
        raise LookupError("Customer not found in this organization.")

    conversation = Conversation(
        organization_id=organization_id,
        customer_id=customer.id,
        subject=payload.subject.strip(),
        priority=payload.priority,
        channel=payload.channel,
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


def list_conversations(
    db: Session,
    organization_id: uuid.UUID,
    status: str | None = None,
    priority: str | None = None,
    assigned_to_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[Conversation]:
    query = select(Conversation).where(
        Conversation.organization_id == organization_id
    )

    if status:
        query = query.where(Conversation.status == status)

    if priority:
        query = query.where(Conversation.priority == priority)

    if assigned_to_id:
        query = query.where(
            Conversation.assigned_to_id == assigned_to_id
        )

    query = (
        query.order_by(Conversation.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(query).all())

def get_conversation(
    db: Session,
    organization_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> Conversation | None:

    query = (
        select(Conversation)
        .options(joinedload(Conversation.customer))
        .where(
            Conversation.id == conversation_id,
            Conversation.organization_id == organization_id,
        )
    )

    return db.scalar(query)


def get_conversation_messages(
    db: Session,
    organization_id: uuid.UUID,
    conversation_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> list[Message] | None:

    conversation = db.scalar(
        select(Conversation.id).where(
            Conversation.id == conversation_id,
            Conversation.organization_id == organization_id,
        )
    )

    if conversation is None:
        return None

    query = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(query).all())