
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.conversation_event import ConversationEvent
from app.models.organization_member import OrganizationMember
from app.models.user import User

from app.services.audit_log_service import record_audit_log

VALID_STATUSES = {
    "open",
    "pending",
    "resolved",
    "closed",
}

VALID_PRIORITIES = {
    "low",
    "normal",
    "high",
    "urgent",
}


def _get_conversation(
    db: Session,
    organization_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> Conversation:

    conversation = db.scalar(
        select(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.organization_id == organization_id,
        )
        .with_for_update()
    )

    if conversation is None:
        raise LookupError("Conversation not found.")

    return conversation


def assign_conversation(
    db: Session,
    organization_id: uuid.UUID,
    conversation_id: uuid.UUID,
    actor_id: uuid.UUID,
    assigned_to_id: uuid.UUID | None,
) -> Conversation:

    try:
        conversation = _get_conversation(
            db,
            organization_id,
            conversation_id,
        )

        if assigned_to_id is not None:
            membership = db.scalar(
                select(OrganizationMember)
                .join(
                    User,
                    User.id == OrganizationMember.user_id,
                )
                .where(
                    OrganizationMember.organization_id == organization_id,
                    OrganizationMember.user_id == assigned_to_id,
                    User.is_active.is_(True),
                )
            )

            if membership is None:
                raise ValueError(
                    "The assigned user must be an active member "
                    "of this organization."
                )

        old_value = (
            str(conversation.assigned_to_id)
            if conversation.assigned_to_id
            else None
        )

        new_value = (
            str(assigned_to_id)
            if assigned_to_id
            else None
        )

        if old_value == new_value:
            return conversation

        conversation.assigned_to_id = assigned_to_id

        event = ConversationEvent(
            conversation_id=conversation.id,
            actor_id=actor_id,
            event_type="assignment_changed",
            old_value=old_value,
            new_value=new_value,
        )

        db.add(event)
        record_audit_log(
            db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="conversation_assigned",
            resource_type="conversation",
            resource_id=conversation.id,
            details={
                "old_assigned_to_id": old_value,
                "new_assigned_to_id": new_value,
            },
        )
        db.commit()
        db.refresh(conversation)

        return conversation

    except Exception:
        db.rollback()
        raise


def update_conversation_status(
    db: Session,
    organization_id: uuid.UUID,
    conversation_id: uuid.UUID,
    actor_id: uuid.UUID,
    new_status: str,
) -> Conversation:

    if new_status not in VALID_STATUSES:
        raise ValueError("Invalid conversation status.")

    try:
        conversation = _get_conversation(
            db,
            organization_id,
            conversation_id,
        )

        old_status = conversation.status

        if old_status == new_status:
            return conversation

        conversation.status = new_status

        event = ConversationEvent(
            conversation_id=conversation.id,
            actor_id=actor_id,
            event_type="status_changed",
            old_value=old_status,
            new_value=new_status,
        )

        db.add(event)
        record_audit_log(
            db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="conversation_status_changed",
            resource_type="conversation",
            resource_id=conversation.id,
            details={
                "old_status": old_status,
                "new_status": new_status,
            },
        )
        db.commit()
        db.refresh(conversation)

        return conversation

    except Exception:
        db.rollback()
        raise


def update_conversation_priority(
    db: Session,
    organization_id: uuid.UUID,
    conversation_id: uuid.UUID,
    actor_id: uuid.UUID,
    new_priority: str,
) -> Conversation:

    if new_priority not in VALID_PRIORITIES:
        raise ValueError("Invalid conversation priority.")

    try:
        conversation = _get_conversation(
            db,
            organization_id,
            conversation_id,
        )

        old_priority = conversation.priority

        if old_priority == new_priority:
            return conversation

        conversation.priority = new_priority

        event = ConversationEvent(
            conversation_id=conversation.id,
            actor_id=actor_id,
            event_type="priority_changed",
            old_value=old_priority,
            new_value=new_priority,
        )

        db.add(event)
        record_audit_log(
            db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="conversation_priority_changed",
            resource_type="conversation",
            resource_id=conversation.id,
            details={
                "old_priority": old_priority,
                "new_priority": new_priority,
            },
        )
        db.commit()
        db.refresh(conversation)

        return conversation

    except Exception:
        db.rollback()
        raise
