
from app.models.user import User
import uuid
def register_owner(client, email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Organization Owner",
            "email": email,
            "password": "OwnerPassword123!",
            "organization_name": "Test Organization",
        },
    )

    assert response.status_code == 201

    data = response.json()

    return {
        "token": data["access_token"],
        "organization_id": data["organization"]["id"],
        "user_id": data["user"]["id"],
    }


def auth_headers(account):
    return {
        "Authorization": f"Bearer {account['token']}",
        "X-Organization-ID": account["organization_id"],
    }


def create_test_customer(client, owner):
    response = client.post(
        "/api/v1/customers",
        headers=auth_headers(owner),
        json={
            "full_name": "Ali Khan",
            "email": "customer@example.com",
            "phone": "03001234567",
            "company": "ABC Technologies",
        },
    )

    assert response.status_code == 201
    return response.json()


def create_test_conversation(
    client,
    owner,
    customer_id,
    subject="Website support request",
):
    return client.post(
        "/api/v1/conversations",
        headers=auth_headers(owner),
        json={
            "customer_id": customer_id,
            "subject": subject,
            "priority": "normal",
            "channel": "web_widget",
        },
    )


def create_test_agent(client, owner):
    invite_response = client.post(
        "/api/v1/team/members",
        headers=auth_headers(owner),
        json={
            "full_name": "Test Agent",
            "email": "agent@example.com",
            "password": "AgentPassword123!",
            "role": "agent",
        },
    )

    assert invite_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "agent@example.com",
            "password": "AgentPassword123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    me_response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 200

    return me_response.json()["id"]


def test_create_conversation_success(client):
    owner = register_owner(client, "owner1@example.com")
    customer = create_test_customer(client, owner)

    response = create_test_conversation(
        client,
        owner,
        customer["id"],
    )

    assert response.status_code == 201

    data = response.json()

    assert data["subject"] == "Website support request"
    assert data["customer_id"] == customer["id"]
    assert data["organization_id"] == owner["organization_id"]
    assert data["priority"] == "normal"
    assert data["status"] == "open"


def test_create_conversation_with_invalid_customer(client):
    owner = register_owner(client, "owner2@example.com")

    response = create_test_conversation(
        client,
        owner,
        "00000000-0000-0000-0000-000000000000",
    )

    assert response.status_code == 404


def test_create_conversation_with_invalid_priority(client):
    owner = register_owner(client, "owner3@example.com")
    customer = create_test_customer(client, owner)

    response = client.post(
        "/api/v1/conversations",
        headers=auth_headers(owner),
        json={
            "customer_id": customer["id"],
            "subject": "Invalid priority test",
            "priority": "super-urgent",
            "channel": "web_widget",
        },
    )

    assert response.status_code == 422


def test_create_conversation_with_invalid_channel(client):
    owner = register_owner(client, "owner4@example.com")
    customer = create_test_customer(client, owner)

    response = client.post(
        "/api/v1/conversations",
        headers=auth_headers(owner),
        json={
            "customer_id": customer["id"],
            "subject": "Invalid channel test",
            "priority": "normal",
            "channel": "email",
        },
    )

    assert response.status_code == 422


def test_list_conversations(client):
    owner = register_owner(client, "owner5@example.com")
    customer = create_test_customer(client, owner)

    first = create_test_conversation(
        client, owner, customer["id"], "First request"
    )
    second = create_test_conversation(
        client, owner, customer["id"], "Second request"
    )

    assert first.status_code == 201
    assert second.status_code == 201

    response = client.get(
        "/api/v1/conversations",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_filter_conversations_by_status(client):
    owner = register_owner(client, "owner6@example.com")
    customer = create_test_customer(client, owner)

    conversation = create_test_conversation(
        client, owner, customer["id"]
    )
    conversation_id = conversation.json()["id"]

    update_response = client.patch(
        f"/api/v1/conversations/{conversation_id}/status",
        headers=auth_headers(owner),
        json={"status": "pending"},
    )

    assert update_response.status_code == 200

    response = client.get(
        "/api/v1/conversations?status=pending",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "pending"


def test_get_conversation_details(client):
    owner = register_owner(client, "owner7@example.com")
    customer = create_test_customer(client, owner)

    create_response = create_test_conversation(
        client, owner, customer["id"]
    )
    conversation_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/conversations/{conversation_id}",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert response.json()["id"] == conversation_id
    assert response.json()["customer"]["id"] == customer["id"]


def test_send_agent_message(client):
    owner = register_owner(client, "owner8@example.com")
    customer = create_test_customer(client, owner)

    conversation = create_test_conversation(
        client, owner, customer["id"]
    )
    conversation_id = conversation.json()["id"]

    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=auth_headers(owner),
        json={"content": "  Hello, how can I help you?  "},
    )

    assert response.status_code == 201

    data = response.json()

    assert data["content"] == "Hello, how can I help you?"
    assert data["sender_type"] == "agent"
    assert data["sender_user_id"] == owner["user_id"]


def test_get_conversation_message_history(client):
    owner = register_owner(client, "owner9@example.com")
    customer = create_test_customer(client, owner)

    conversation = create_test_conversation(
        client, owner, customer["id"]
    )
    conversation_id = conversation.json()["id"]

    client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=auth_headers(owner),
        json={"content": "First message"},
    )

    client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=auth_headers(owner),
        json={"content": "Second message"},
    )

    response = client.get(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["content"] == "First message"
    assert response.json()[1]["content"] == "Second message"


def test_cannot_send_message_to_closed_conversation(client):
    owner = register_owner(client, "owner10@example.com")
    customer = create_test_customer(client, owner)

    conversation = create_test_conversation(
        client, owner, customer["id"]
    )
    conversation_id = conversation.json()["id"]

    status_response = client.patch(
        f"/api/v1/conversations/{conversation_id}/status",
        headers=auth_headers(owner),
        json={"status": "closed"},
    )

    assert status_response.status_code == 200

    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=auth_headers(owner),
        json={"content": "This message should be rejected"},
    )

    assert response.status_code == 409
    assert "closed conversation" in response.json()["detail"]


def test_assign_conversation_to_team_member(client):
    owner = register_owner(client, "owner11@example.com")
    customer = create_test_customer(client, owner)
    agent_id = create_test_agent(client, owner)

    conversation = create_test_conversation(
        client, owner, customer["id"]
    )
    conversation_id = conversation.json()["id"]

    response = client.patch(
        f"/api/v1/conversations/{conversation_id}/assignment",
        headers=auth_headers(owner),
        json={"assigned_to_id": agent_id},
    )

    assert response.status_code == 200
    assert response.json()["assigned_to_id"] == agent_id


def test_reject_assignment_to_non_member(client):
    owner_one = register_owner(client, "owner12@example.com")
    owner_two = register_owner(client, "owner13@example.com")

    customer = create_test_customer(client, owner_one)

    conversation = create_test_conversation(
        client, owner_one, customer["id"]
    )
    conversation_id = conversation.json()["id"]

    response = client.patch(
        f"/api/v1/conversations/{conversation_id}/assignment",
        headers=auth_headers(owner_one),
        json={"assigned_to_id": owner_two["user_id"]},
    )

    assert response.status_code == 422
    assert "active member" in response.json()["detail"]

def test_update_conversation_status_and_record_event(client):
    owner = register_owner(client, "owner14@example.com")
    customer = create_test_customer(client, owner)

    conversation = create_test_conversation(
        client, owner, customer["id"]
    )
    conversation_id = conversation.json()["id"]

    response = client.patch(
        f"/api/v1/conversations/{conversation_id}/status",
        headers=auth_headers(owner),
        json={"status": "pending"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "pending"

    events_response = client.get(
        f"/api/v1/conversations/{conversation_id}/events",
        headers=auth_headers(owner),
    )

    assert events_response.status_code == 200

    events = events_response.json()

    assert len(events) == 1
    assert events[0]["event_type"] == "status_changed"
    assert events[0]["old_value"] == "open"
    assert events[0]["new_value"] == "pending"


def test_update_conversation_priority_and_record_event(client):
    owner = register_owner(client, "owner15@example.com")
    customer = create_test_customer(client, owner)

    conversation = create_test_conversation(
        client, owner, customer["id"]
    )
    conversation_id = conversation.json()["id"]

    response = client.patch(
        f"/api/v1/conversations/{conversation_id}/priority",
        headers=auth_headers(owner),
        json={"priority": "urgent"},
    )

    assert response.status_code == 200
    assert response.json()["priority"] == "urgent"

    events_response = client.get(
        f"/api/v1/conversations/{conversation_id}/events",
        headers=auth_headers(owner),
    )

    assert events_response.status_code == 200

    events = events_response.json()

    assert len(events) == 1
    assert events[0]["event_type"] == "priority_changed"
    assert events[0]["old_value"] == "normal"
    assert events[0]["new_value"] == "urgent"


def test_unchanged_status_does_not_create_event(client):
    owner = register_owner(client, "owner16@example.com")
    customer = create_test_customer(client, owner)

    conversation = create_test_conversation(
        client, owner, customer["id"]
    )
    conversation_id = conversation.json()["id"]

    response = client.patch(
        f"/api/v1/conversations/{conversation_id}/status",
        headers=auth_headers(owner),
        json={"status": "open"},
    )

    assert response.status_code == 200

    events_response = client.get(
        f"/api/v1/conversations/{conversation_id}/events",
        headers=auth_headers(owner),
    )

    assert events_response.status_code == 200
    assert events_response.json() == []


def test_user_cannot_access_another_organizations_conversation(client):
    owner_one = register_owner(client, "owner17@example.com")
    owner_two = register_owner(client, "owner18@example.com")

    customer = create_test_customer(client, owner_two)

    conversation = create_test_conversation(
        client, owner_two, customer["id"]
    )
    conversation_id = conversation.json()["id"]

    response = client.get(
        f"/api/v1/conversations/{conversation_id}",
        headers=auth_headers(owner_one),
    )

    assert response.status_code == 404


def test_cannot_read_events_of_another_organizations_conversation(client):
    owner_one = register_owner(client, "owner19@example.com")
    owner_two = register_owner(client, "owner20@example.com")

    customer = create_test_customer(client, owner_two)

    conversation = create_test_conversation(
        client, owner_two, customer["id"]
    )
    conversation_id = conversation.json()["id"]

    response = client.get(
        f"/api/v1/conversations/{conversation_id}/events",
        headers=auth_headers(owner_one),
    )

    assert response.status_code == 404



def test_cannot_assign_conversation_to_inactive_user(client, db_session):
    owner = register_owner(client, "inactive_owner@example.com")
    agent_id = create_test_agent(client, owner)

    customer = create_test_customer(client, owner)
    conversation = create_test_conversation(
        client, owner, customer["id"]
    )

    # Deactivate the agent's account.
    agent_user = db_session.get(User, uuid.UUID(agent_id))
    assert agent_user is not None

    agent_user.is_active = False
    db_session.commit()

    response = client.patch(
        f"/api/v1/conversations/{conversation.json()['id']}/assignment",
        headers=auth_headers(owner),
        json={"assigned_to_id": agent_id},
    )

    assert response.status_code == 422
    assert "active member" in response.json()["detail"]

