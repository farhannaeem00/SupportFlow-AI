from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message

def create_agent_message(
    db: Session,
    organization_id: UUID,
    conversation_id: UUID,
    agent_id: UUID,
    content: str,
) -> Message:

    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.organization_id == organization_id,
        )
    )

    if conversation is None:
        raise LookupError("Conversation not found.")

    if conversation.status == "closed":
        raise ValueError("Cannot send messages to a closed conversation.")

    message = Message(
        conversation_id=conversation.id,
        sender_type="agent",
        sender_user_id=agent_id,
        sender_customer_id=None,
        content=content.strip(),
        message_type="text",
    )

    try:
        db.add(message)
        db.commit()
        db.refresh(message)
        return message
    except Exception:
        db.rollback()
        raise