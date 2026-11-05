
from app.api.v1.endpoints import widget

from tests.test_conversations import (
    auth_headers,
    create_test_customer,
    create_test_conversation,
    register_owner,
)

from tests.test_widget_security import (
    create_widget_conversation,
    create_widget_session,
    register_widget_organization,
    widget_headers,
)


def test_authenticated_customer_support_workflow(
    client,
):
    """Test the authenticated customer support lifecycle."""

    # 1. Register an organization owner.
    owner = register_owner(
        client,
        "workflow_owner@example.com",
    )

    headers = auth_headers(owner)

    # 2. Create a customer.
    customer = create_test_customer(
        client,
        owner,
    )

    # 3. Create a conversation for that customer.
    conversation_response = create_test_conversation(
        client,
        owner,
        customer["id"],
        subject="Integration workflow test",
    )

    assert conversation_response.status_code == 201

    conversation_id = conversation_response.json()["id"]

    # 4. Send an agent message.
    message_response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=headers,
        json={
            "content": "Hello! We are reviewing your request."
        },
    )

    assert message_response.status_code == 201
    assert message_response.json()["sender_type"] == "agent"

    # 5. Update conversation status.
    status_response = client.patch(
        f"/api/v1/conversations/{conversation_id}/status",
        headers=headers,
        json={"status": "pending"},
    )

    assert status_response.status_code == 200
    assert status_response.json()["status"] == "pending"

    # 6. Update conversation priority.
    priority_response = client.patch(
        f"/api/v1/conversations/{conversation_id}/priority",
        headers=headers,
        json={"priority": "urgent"},
    )

    assert priority_response.status_code == 200
    assert priority_response.json()["priority"] == "urgent"

    # 7. Verify conversation message history.
    messages_response = client.get(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=headers,
    )

    assert messages_response.status_code == 200

    messages = messages_response.json()

    assert len(messages) == 1
    assert messages[0]["content"] == (
        "Hello! We are reviewing your request."
    )

    # 8. Verify conversation event history.
    events_response = client.get(
        f"/api/v1/conversations/{conversation_id}/events",
        headers=headers,
    )

    assert events_response.status_code == 200

    events = events_response.json()

    event_types = {
        event["event_type"]
        for event in events
    }

    assert "status_changed" in event_types
    assert "priority_changed" in event_types

    # 9. Verify final conversation state.
    details_response = client.get(
        f"/api/v1/conversations/{conversation_id}",
        headers=headers,
    )

    assert details_response.status_code == 200

    conversation = details_response.json()

    assert conversation["customer_id"] == customer["id"]
    assert conversation["organization_id"] == owner["organization_id"]
    assert conversation["status"] == "pending"
    assert conversation["priority"] == "urgent"


def test_complete_website_widget_support_workflow(
    client,
    monkeypatch,
):
    """Test widget session, conversation, messages and history."""

    # Prevent external AI provider calls during this integration test.
    monkeypatch.setattr(
        widget,
        "process_widget_ai",
        lambda **kwargs: None,
    )

    # 1. Register an organization with a public widget key.
    organization = register_widget_organization(
        client,
        "widget_workflow@example.com",
    )

    public_key = organization["public_key"]

    # 2. Create a widget visitor session.
    session_response = create_widget_session(
        client,
        public_key,
    )

    assert session_response.status_code == 201

    session_token = session_response.json()["session_token"]
    headers = widget_headers(session_token)

    # 3. Create a conversation through the public widget.
    conversation_response = create_widget_conversation(
        client,
        public_key,
        session_token,
    )

    assert conversation_response.status_code == 201

    conversation = conversation_response.json()

    assert conversation["id"]
    assert conversation["subject"] == "Widget security test"

    initial_messages = conversation["messages"]

    assert len(initial_messages) >= 1

    # 4. Send another visitor message.
    message_response = client.post(
        f"/api/v1/widget/{public_key}/messages",
        headers=headers,
        json={
            "message": "I also need help with my account."
        },
    )

    assert message_response.status_code == 201

    message = message_response.json()

    assert message["content"] == (
        "I also need help with my account."
    )
    assert message["sender_type"] == "customer"

    # 5. Retrieve the complete conversation history.
    history_response = client.get(
        f"/api/v1/widget/{public_key}/conversation",
        headers=headers,
    )

    assert history_response.status_code == 200

    history = history_response.json()

    assert history["id"] == conversation["id"]

    messages = history["messages"]

    assert len(messages) >= 2

    message_contents = [
        item["content"]
        for item in messages
    ]

    assert "I need assistance." in message_contents
    assert "I also need help with my account." in message_contents

    # 6. Verify the same session cannot create a second conversation.
    duplicate_response = create_widget_conversation(
        client,
        public_key,
        session_token,
    )

    assert duplicate_response.status_code == 409
