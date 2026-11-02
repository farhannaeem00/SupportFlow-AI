import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.conversation_event import ConversationEvent


def get_conversation_events(
    db: Session,
    organization_id: uuid.UUID,
    conversation_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> list[ConversationEvent] | None:

    # Verify that the conversation belongs to this organization.
    conversation = db.scalar(
        select(Conversation.id).where(
            Conversation.id == conversation_id,
            Conversation.organization_id == organization_id,
        )
    )

    if conversation is None:
        return None

    # Retrieve events in chronological order.
    query = (
        select(ConversationEvent)
        .where(
            ConversationEvent.conversation_id == conversation_id
        )
        .order_by(
            ConversationEvent.created_at.asc(),
            ConversationEvent.id.asc(),
        )
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(query).all())