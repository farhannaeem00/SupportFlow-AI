
import logging
from uuid import UUID

from sqlalchemy import select

from app.database import SessionLocal
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.user import User
from app.services.email_service import send_email


logger = logging.getLogger(__name__)


def _get_conversation_context(db, organization_id, conversation_id):
    """Load a conversation only when it belongs to the given organization."""

    result = db.execute(
        select(Conversation, Organization, Customer)
        .join(
            Organization,
            Organization.id == Conversation.organization_id,
        )
        .join(
            Customer,
            Customer.id == Conversation.customer_id,
        )
        .where(
            Conversation.id == conversation_id,
            Conversation.organization_id == organization_id,
            Organization.is_active.is_(True),
        )
    ).first()

    return result


def _get_owner_recipients(db, organization_id):
    """Return active organization owners as (id, name, email) tuples."""

    return list(
        db.execute(
            select(User.id, User.full_name, User.email)
            .join(
                OrganizationMember,
                OrganizationMember.user_id == User.id,
            )
            .where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.role == "owner",
                User.is_active.is_(True),
            )
            .distinct()
        ).all()
    )


def _get_assigned_recipient(db, organization_id, assigned_to_id):
    """Return the assigned active organization member, if valid."""

    if assigned_to_id is None:
        return None

    return db.execute(
        select(User.id, User.full_name, User.email)
        .join(
            OrganizationMember,
            OrganizationMember.user_id == User.id,
        )
        .where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == assigned_to_id,
            User.is_active.is_(True),
        )
    ).first()


def _deliver(recipients, subject, body):
    """Attempt delivery independently for each recipient."""

    seen = set()

    for recipient in recipients:
        if recipient is None:
            continue

        email = recipient.email

        if not email or email in seen:
            continue

        seen.add(email)

        try:
            send_email(
                to_email=email,
                subject=subject,
                body=body,
            )
        except Exception:
            logger.exception(
                "Notification email delivery failed for %s.",
                email,
            )


def _run_notification(
    organization_id: UUID,
    conversation_id: UUID,
    notification_type: str,
    assigned_to_id: UUID | None = None,
) -> None:
    """Run a notification using an independent database session."""

    try:
        with SessionLocal() as db:
            context = _get_conversation_context(
                db,
                organization_id,
                conversation_id,
            )

            if context is None:
                logger.warning(
                    "Skipping %s notification: conversation %s "
                    "was not found in organization %s.",
                    notification_type,
                    conversation_id,
                    organization_id,
                )
                return

            conversation, organization, customer = context

            owners = _get_owner_recipients(
                db,
                organization_id,
            )

            assigned = _get_assigned_recipient(
                db,
                organization_id,
                assigned_to_id or conversation.assigned_to_id,
            )

            subject = ""
            body = ""
            recipients = []

            if notification_type == "new_conversation":
                recipients = owners
                subject = "New customer conversation"
                body = (
                    f"A new customer conversation has been received.\n\n"
                    f"Organization: {organization.name}\n"
                    f"Customer: {customer.full_name}\n"
                    f"Subject: {conversation.subject}\n"
                    f"Priority: {conversation.priority}\n\n"
                    "Please review it in your SupportFlow AI dashboard."
                )

            elif notification_type == "customer_message":
                recipients = [assigned] if assigned else owners
                subject = "New customer message"
                body = (
                    f"A customer has sent a new message.\n\n"
                    f"Organization: {organization.name}\n"
                    f"Customer: {customer.full_name}\n"
                    f"Subject: {conversation.subject}\n\n"
                    "Please review the conversation in your "
                    "SupportFlow AI dashboard."
                )

            elif notification_type == "assignment":
                recipients = [assigned]
                subject = "Conversation assigned to you"
                body = (
                    f"A conversation has been assigned to you.\n\n"
                    f"Organization: {organization.name}\n"
                    f"Customer: {customer.full_name}\n"
                    f"Subject: {conversation.subject}\n\n"
                    "Please review it in your SupportFlow AI dashboard."
                )

            elif notification_type == "urgent":
                recipients = list(owners)
                if assigned:
                    recipients.append(assigned)

                subject = "Urgent customer conversation"
                body = (
                    f"A conversation has been marked urgent.\n\n"
                    f"Organization: {organization.name}\n"
                    f"Customer: {customer.full_name}\n"
                    f"Subject: {conversation.subject}\n\n"
                    "Please review it as soon as possible."
                )

            elif notification_type == "resolved":
                recipients = [assigned]
                subject = "Conversation resolved"
                body = (
                    f"A conversation assigned to you has been resolved.\n\n"
                    f"Organization: {organization.name}\n"
                    f"Customer: {customer.full_name}\n"
                    f"Subject: {conversation.subject}\n\n"
                    "You can review its history in your dashboard."
                )

            _deliver(recipients, subject, body)

    except Exception:
        logger.exception(
            "Notification task %s failed for conversation %s.",
            notification_type,
            conversation_id,
        )


def notify_new_widget_conversation(
    organization_id: UUID,
    conversation_id: UUID,
) -> None:
    _run_notification(
        organization_id,
        conversation_id,
        "new_conversation",
    )


def notify_customer_message(
    organization_id: UUID,
    conversation_id: UUID,
) -> None:
    _run_notification(
        organization_id,
        conversation_id,
        "customer_message",
    )


def notify_conversation_assigned(
    organization_id: UUID,
    conversation_id: UUID,
    assigned_to_id: UUID,
) -> None:
    _run_notification(
        organization_id,
        conversation_id,
        "assignment",
        assigned_to_id,
    )


def notify_conversation_urgent(
    organization_id: UUID,
    conversation_id: UUID,
) -> None:
    _run_notification(
        organization_id,
        conversation_id,
        "urgent",
    )


def notify_conversation_resolved(
    organization_id: UUID,
    conversation_id: UUID,
) -> None:
    _run_notification(
        organization_id,
        conversation_id,
        "resolved",
    )
