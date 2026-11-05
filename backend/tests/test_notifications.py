
from uuid import uuid4

import pytest
from sqlalchemy.orm import sessionmaker

from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.user import User
from app.services import notification_service


@pytest.fixture
def notification_setup(db_session, monkeypatch):
    """Create an isolated organization and bind notifications to its test transaction."""

    notification_session_factory = sessionmaker(
        bind=db_session.connection(),
        autoflush=False,
        autocommit=False,
        join_transaction_mode="create_savepoint",
    )

    monkeypatch.setattr(
        notification_service,
        "SessionLocal",
        notification_session_factory,
    )

    organization = Organization(
        name="Notification Test Organization",
        slug=f"notification-test-{uuid4().hex}",
    )

    owner = User(
        full_name="Test Owner",
        email=f"owner-{uuid4().hex}@example.com",
        hashed_password="test-hash",
        is_active=True,
    )

    agent = User(
        full_name="Test Agent",
        email=f"agent-{uuid4().hex}@example.com",
        hashed_password="test-hash",
        is_active=True,
    )

    customer = None

    db_session.add_all([organization, owner, agent])
    db_session.flush()

    db_session.add_all([
        OrganizationMember(
            organization_id=organization.id,
            user_id=owner.id,
            role="owner",
        ),
        OrganizationMember(
            organization_id=organization.id,
            user_id=agent.id,
            role="agent",
        ),
    ])

    customer = Customer(
        organization_id=organization.id,
        full_name="Test Customer",
        email="customer@example.com",
    )

    db_session.add(customer)
    db_session.flush()

    conversation = Conversation(
        organization_id=organization.id,
        customer_id=customer.id,
        subject="Test support request",
        status="open",
        priority="normal",
        channel="web_widget",
    )

    db_session.add(conversation)
    db_session.flush()

    return {
        "organization": organization,
        "owner": owner,
        "agent": agent,
        "customer": customer,
        "conversation": conversation,
    }


@pytest.fixture
def sent_emails(monkeypatch):
    emails = []

    def fake_send_email(to_email, subject, body):
        emails.append({
            "to": to_email,
            "subject": subject,
            "body": body,
        })

    monkeypatch.setattr(
        notification_service,
        "send_email",
        fake_send_email,
    )

    return emails


def test_new_widget_conversation_notifies_active_owners(
    notification_setup,
    sent_emails,
):
    data = notification_setup

    notification_service.notify_new_widget_conversation(
        data["organization"].id,
        data["conversation"].id,
    )

    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == data["owner"].email
    assert "New customer conversation" in sent_emails[0]["subject"]


def test_customer_message_notifies_assigned_agent(
    db_session,
    notification_setup,
    sent_emails,
):
    data = notification_setup
    conversation = data["conversation"]
    agent = data["agent"]

    conversation.assigned_to_id = agent.id
    db_session.flush()

    notification_service.notify_customer_message(
        data["organization"].id,
        conversation.id,
    )

    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == agent.email


def test_unassigned_customer_message_notifies_owners(
    notification_setup,
    sent_emails,
):
    data = notification_setup

    notification_service.notify_customer_message(
        data["organization"].id,
        data["conversation"].id,
    )

    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == data["owner"].email


def test_assignment_notification_only_goes_to_assigned_agent(
    notification_setup,
    sent_emails,
):
    data = notification_setup

    notification_service.notify_conversation_assigned(
        data["organization"].id,
        data["conversation"].id,
        data["agent"].id,
    )

    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == data["agent"].email
    assert "assigned" in sent_emails[0]["subject"].lower()


def test_urgent_notification_goes_to_owner_and_assigned_agent(
    db_session,
    notification_setup,
    sent_emails,
):
    data = notification_setup
    conversation = data["conversation"]

    conversation.assigned_to_id = data["agent"].id
    db_session.flush()

    notification_service.notify_conversation_urgent(
        data["organization"].id,
        conversation.id,
    )

    recipients = {email["to"] for email in sent_emails}

    assert recipients == {
        data["owner"].email,
        data["agent"].email,
    }


def test_urgent_notification_deduplicates_owner_and_agent_email(
    db_session,
    notification_setup,
    sent_emails,
):
    data = notification_setup
    owner = data["owner"]
    conversation = data["conversation"]

    agent_membership = db_session.query(OrganizationMember).filter_by(
        organization_id=data["organization"].id,
        user_id=data["agent"].id,
    ).one()

    db_session.delete(agent_membership)

    conversation.assigned_to_id = owner.id
    db_session.flush()

    notification_service.notify_conversation_urgent(
        data["organization"].id,
        conversation.id,
    )

    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == owner.email


def test_inactive_assigned_agent_falls_back_to_owner(
    db_session,
    notification_setup,
    sent_emails,
):
    data = notification_setup
    agent = data["agent"]

    agent.is_active = False
    data["conversation"].assigned_to_id = agent.id
    db_session.flush()

    notification_service.notify_customer_message(
        data["organization"].id,
        data["conversation"].id,
    )

    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == data["owner"].email


def test_resolved_notification_goes_to_assigned_agent(
    db_session,
    notification_setup,
    sent_emails,
):
    data = notification_setup
    conversation = data["conversation"]

    conversation.assigned_to_id = data["agent"].id
    db_session.flush()

    notification_service.notify_conversation_resolved(
        data["organization"].id,
        conversation.id,
    )

    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == data["agent"].email


def test_notification_does_not_send_for_another_organization(
    notification_setup,
    sent_emails,
):
    data = notification_setup

    notification_service.notify_new_widget_conversation(
        uuid4(),
        data["conversation"].id,
    )

    assert sent_emails == []


def test_inactive_organization_does_not_receive_notifications(
    db_session,
    notification_setup,
    sent_emails,
):
    data = notification_setup
    data["organization"].is_active = False
    db_session.flush()

    notification_service.notify_new_widget_conversation(
        data["organization"].id,
        data["conversation"].id,
    )

    assert sent_emails == []


def test_email_failure_does_not_raise_exception(
    monkeypatch,
    notification_setup,
):
    data = notification_setup

    def failing_send_email(*args, **kwargs):
        raise RuntimeError("SMTP unavailable")

    monkeypatch.setattr(
        notification_service,
        "send_email",
        failing_send_email,
    )

    notification_service.notify_new_widget_conversation(
        data["organization"].id,
        data["conversation"].id,
    )
