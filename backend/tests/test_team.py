

from sqlalchemy import select

from app.models import AuditLog, User
def register_owner(client, email="owner@example.com"):
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
    }


def auth_headers(account):
    return {
        "Authorization": f"Bearer {account['token']}",
        "X-Organization-ID": account["organization_id"],
    }


def invite_agent(client, owner, email="agent@example.com"):
    return client.post(
        "/api/v1/team/members",
        headers=auth_headers(owner),
        json={
            "full_name": "Test Agent",
            "email": email,
            "password": "AgentPassword123!",
            "role": "agent",
        },
    )


def test_owner_can_list_team_members(client):
    owner = register_owner(client)

    response = client.get(
        "/api/v1/team/members",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["role"] == "owner"


def test_owner_can_invite_agent(client):
    owner = register_owner(client)

    response = invite_agent(client, owner)

    assert response.status_code == 201
    assert response.json()["message"] == "Team member created successfully"
    assert response.json()["member_id"]


def test_owner_can_update_agent_role(client):
    owner = register_owner(client)

    invite_response = invite_agent(client, owner)
    assert invite_response.status_code == 201

    member_id = invite_response.json()["member_id"]

    response = client.patch(
        f"/api/v1/team/members/{member_id}/role",
        headers=auth_headers(owner),
        json={"role": "owner"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Member role updated successfully"


def test_owner_can_remove_agent(client):
    owner = register_owner(client)

    invite_response = invite_agent(client, owner)
    assert invite_response.status_code == 201

    member_id = invite_response.json()["member_id"]

    response = client.delete(
        f"/api/v1/team/members/{member_id}",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200

    members_response = client.get(
        "/api/v1/team/members",
        headers=auth_headers(owner),
    )

    assert members_response.status_code == 200
    assert len(members_response.json()) == 1


def test_last_owner_cannot_demote_themselves(client):
    owner = register_owner(client)

    response = client.patch(
        f"/api/v1/team/members/{_get_owner_member_id(client, owner)}/role",
        headers=auth_headers(owner),
        json={"role": "agent"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "An organization must have at least one owner"
    )


def _get_owner_member_id(client, owner):
    response = client.get(
        "/api/v1/team/members",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200

    return response.json()[0]["id"]


def test_owner_cannot_remove_themselves(client):
    owner = register_owner(client)

    member_id = _get_owner_member_id(client, owner)

    response = client.delete(
        f"/api/v1/team/members/{member_id}",
        headers=auth_headers(owner),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "You cannot remove your own membership"
    )


def test_agent_cannot_invite_team_members(client):
    owner = register_owner(client)

    invite_response = invite_agent(client, owner)
    assert invite_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "agent@example.com",
            "password": "AgentPassword123!",
        },
    )

    assert login_response.status_code == 200

    agent = {
        "token": login_response.json()["access_token"],
        "organization_id": owner["organization_id"],
    }

    response = invite_agent(
        client,
        agent,
        email="another-agent@example.com",
    )

    assert response.status_code == 403


def test_user_cannot_access_another_organization(client):
    owner_one = register_owner(client, "owner1@example.com")
    owner_two = register_owner(client, "owner2@example.com")

    response = client.get(
        "/api/v1/team/members",
        headers={
            "Authorization": f"Bearer {owner_one['token']}",
            "X-Organization-ID": owner_two["organization_id"],
        },
    )

    assert response.status_code == 403

def test_owner_cannot_invite_member_with_invalid_role(client):
    owner = register_owner(client)

    response = client.post(
        "/api/v1/team/members",
        headers=auth_headers(owner),
        json={
            "full_name": "Invalid Role User",
            "email": "invalid_role@example.com",
            "password": "AgentPassword123!",
            "role": "superadmin",
        },
    )

    assert response.status_code == 422


def test_owner_cannot_assign_invalid_role(client):
    owner = register_owner(client)

    invite_response = invite_agent(client, owner)
    assert invite_response.status_code == 201

    member_id = invite_response.json()["member_id"]

    response = client.patch(
        f"/api/v1/team/members/{member_id}/role",
        headers=auth_headers(owner),
        json={"role": "superadmin"},
    )

    assert response.status_code == 422

def test_team_operations_create_audit_logs(client, db_session):
    owner = register_owner(client)

    owner_user = db_session.scalar(
        select(User).where(User.email == "owner@example.com")
    )

    # Invite a team member.
    invite_response = invite_agent(client, owner)
    assert invite_response.status_code == 201

    member_id = invite_response.json()["member_id"]

    # Change the member's role.
    role_response = client.patch(
        f"/api/v1/team/members/{member_id}/role",
        headers=auth_headers(owner),
        json={"role": "owner"},
    )
    assert role_response.status_code == 200

    # Requesting the same role must not create another audit record.
    unchanged_response = client.patch(
        f"/api/v1/team/members/{member_id}/role",
        headers=auth_headers(owner),
        json={"role": "owner"},
    )
    assert unchanged_response.status_code == 200

    # Remove the team member.
    delete_response = client.delete(
        f"/api/v1/team/members/{member_id}",
        headers=auth_headers(owner),
    )
    assert delete_response.status_code == 200

    logs = db_session.scalars(
        select(AuditLog)
        .where(
            AuditLog.organization_id == owner["organization_id"],
            AuditLog.resource_id == member_id,
        )
        .order_by(AuditLog.created_at.asc())
    ).all()

    assert len(logs) == 3

    assert [log.action for log in logs] == [
        "team_member_invited",
        "team_member_role_changed",
        "team_member_removed",
    ]

    assert all(log.resource_type == "team_member" for log in logs)
    assert all(log.actor_id == owner_user.id for log in logs)

    assert logs[0].details["role"] == "agent"
    assert logs[0].details["user_id"]

    assert logs[1].details["old_role"] == "agent"
    assert logs[1].details["new_role"] == "owner"

    assert logs[2].details["role"] == "owner"
    assert logs[2].details["user_id"] == logs[0].details["user_id"]


def test_failed_team_operations_create_no_audit_logs(client, db_session):
    owner = register_owner(client)

    owner_member_id = _get_owner_member_id(client, owner)

    # The last owner cannot demote themselves.
    demote_response = client.patch(
        f"/api/v1/team/members/{owner_member_id}/role",
        headers=auth_headers(owner),
        json={"role": "agent"},
    )
    assert demote_response.status_code == 409

    # The owner cannot remove their own membership.
    remove_response = client.delete(
        f"/api/v1/team/members/{owner_member_id}",
        headers=auth_headers(owner),
    )
    assert remove_response.status_code == 409

    logs = db_session.scalars(
        select(AuditLog).where(
            AuditLog.organization_id == owner["organization_id"]
        )
    ).all()

    assert logs == []