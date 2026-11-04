
import hashlib
import secrets
import uuid

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Organization,
    Customer,
    Conversation,
    Message,
    WidgetSession,
)


SESSION_LIFETIME_DAYS = 7


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_active_organization(
    db: Session,
    public_key: str,
) -> Organization | None:
    return db.scalar(
        select(Organization).where(
            Organization.public_key == public_key,
            Organization.is_active.is_(True),
        )
    )


def create_widget_session(
    db: Session,
    organization: Organization,
) -> tuple[WidgetSession, str]:
    raw_token = secrets.token_urlsafe(32)

    now = datetime.now(timezone.utc)

    session = WidgetSession(
        organization_id=organization.id,
        token_hash=_hash_token(raw_token),
        expires_at=now + timedelta(days=SESSION_LIFETIME_DAYS),
        last_seen_at=now,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session, raw_token


def get_valid_widget_session(
    db: Session,
    organization_id: uuid.UUID,
    raw_token: str,
) -> WidgetSession | None:
    session = db.scalar(
        select(WidgetSession).where(
            WidgetSession.organization_id == organization_id,
            WidgetSession.token_hash == _hash_token(raw_token),
        )
    )

    if session is None:
        return None

    now = datetime.now(timezone.utc)

    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= now:
        return None

    session.last_seen_at = now
    db.flush()

    return session


def start_widget_conversation(
    db: Session,
    organization: Organization,
    widget_session: WidgetSession,
    full_name: str,
    email: str | None,
    subject: str,
    message_content: str,
) -> Conversation:

    try:
        normalized_email = email.strip().lower() if email else None

        customer = None

        if normalized_email:
            customer = db.scalar(
                select(Customer).where(
                    Customer.organization_id == organization.id,
                    Customer.email == normalized_email,
                    Customer.is_active.is_(True),
                )
            )

        if customer is None:
            customer = Customer(
                organization_id=organization.id,
                full_name=full_name.strip(),
                email=normalized_email,
            )
            db.add(customer)
            db.flush()

        conversation = Conversation(
            organization_id=organization.id,
            customer_id=customer.id,
            subject=subject.strip(),
            status="open",
            priority="normal",
            channel="web_widget",
        )

        db.add(conversation)
        db.flush()

        initial_message = Message(
            conversation_id=conversation.id,
            sender_type="customer",
            sender_customer_id=customer.id,
            content=message_content.strip(),
            message_type="text",
        )

        db.add(initial_message)

        widget_session.customer_id = customer.id
        widget_session.conversation_id = conversation.id

        db.commit()
        db.refresh(conversation)

        return conversation

    except Exception:
        db.rollback()
        raise


def send_widget_message(
    db: Session,
    widget_session: WidgetSession,
    message_content: str,
) -> Message:

    if not widget_session.conversation_id:
        raise ValueError("Start a conversation before sending messages.")

    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == widget_session.conversation_id,
            Conversation.organization_id == widget_session.organization_id,
        )
    )

    if conversation is None:
        raise LookupError("Conversation not found.")

    if conversation.status == "closed":
        raise ValueError("This conversation is closed.")

    if not widget_session.customer_id:
        raise ValueError("Invalid visitor session.")

    message = Message(
        conversation_id=conversation.id,
        sender_type="customer",
        sender_customer_id=widget_session.customer_id,
        content=message_content.strip(),
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


def get_widget_conversation(
    db: Session,
    widget_session: WidgetSession,
) -> Conversation:

    if not widget_session.conversation_id:
        raise LookupError("No conversation has been started.")

    conversation = db.scalar(
    select(Conversation).where(
        Conversation.id == widget_session.conversation_id,
        Conversation.organization_id == widget_session.organization_id,
    )
)
    if conversation is None:
        raise LookupError("Conversation not found.")

    return conversation


def get_widget_messages(
    db: Session,
    organization_id: uuid.UUID,
    conversation_id: uuid.UUID,
):
    return db.scalars(
        select(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Message.conversation_id == conversation_id,
            Conversation.organization_id == organization_id,
        )
        .order_by(Message.created_at.asc())
    ).all()
