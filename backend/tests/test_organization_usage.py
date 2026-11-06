


def register_owner(client, email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Organization Owner",
            "email": email,
            "password": "OwnerPassword123!",
            "organization_name": "Usage Test Organization",
        },
    )

    assert response.status_code == 201, response.text

    data = response.json()

    return {
        "Authorization": f"Bearer {data['access_token']}",
        "X-Organization-ID": data["organization"]["id"],
    }




def test_get_organization_usage(client):
    headers = register_owner(client, "usage-owner@example.com")

    response = client.get(
        "/api/v1/organizations/current/usage",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["usage"]["team_members"] == 1
    assert data["usage"]["knowledge_bases"] == 0
    assert data["usage"]["documents"] == 0
    assert data["usage"]["storage_bytes"] == 0
    assert data["usage"]["monthly_conversations"] == 0
    assert data["usage"]["monthly_ai_operations"] == 0
    assert data["usage"]["monthly_ai_operations_reserved"] == 0

    assert data["limits"] == {
        "team_members": None,
        "knowledge_bases": None,
        "documents": None,
        "storage_bytes": None,
        "monthly_conversations": None,
        "monthly_ai_operations": None,
    }

    assert data["usage"]["period_start"]


def test_owner_can_update_organization_usage_limits(client):
    headers = register_owner(client, "usage-update@example.com")

    response = client.patch(
        "/api/v1/organizations/current/usage-limits",
        headers=headers,
        json={
            "max_team_members": 5,
            "max_documents": 20,
            "max_storage_bytes": 1048576,
        },
    )

    assert response.status_code == 200, response.text

    assert response.json() == {
        "team_members": 5,
        "knowledge_bases": None,
        "documents": 20,
        "storage_bytes": 1048576,
        "monthly_conversations": None,
        "monthly_ai_operations": None,
    }


def test_usage_limit_update_preserves_omitted_fields(client):
    headers = register_owner(client, "usage-preserve@example.com")

    first_response = client.patch(
        "/api/v1/organizations/current/usage-limits",
        headers=headers,
        json={
            "max_team_members": 5,
            "max_documents": 20,
        },
    )

    assert first_response.status_code == 200

    second_response = client.patch(
        "/api/v1/organizations/current/usage-limits",
        headers=headers,
        json={
            "max_documents": 30,
        },
    )

    assert second_response.status_code == 200
    assert second_response.json()["team_members"] == 5
    assert second_response.json()["documents"] == 30


def test_null_usage_limit_resets_limit_to_unlimited(client):
    headers = register_owner(client, "usage-unlimited@example.com")

    first_response = client.patch(
        "/api/v1/organizations/current/usage-limits",
        headers=headers,
        json={"max_documents": 20},
    )

    assert first_response.status_code == 200
    assert first_response.json()["documents"] == 20

    second_response = client.patch(
        "/api/v1/organizations/current/usage-limits",
        headers=headers,
        json={"max_documents": None},
    )

    assert second_response.status_code == 200
    assert second_response.json()["documents"] is None


def test_organizations_cannot_access_each_others_usage_limits(client):
    organization_a = register_owner(
        client,
        "usage-tenant-a@example.com",
    )
    organization_b = register_owner(
        client,
        "usage-tenant-b@example.com",
    )

    update_response = client.patch(
        "/api/v1/organizations/current/usage-limits",
        headers=organization_a,
        json={"max_documents": 10},
    )

    assert update_response.status_code == 200

    response_a = client.get(
        "/api/v1/organizations/current/usage",
        headers=organization_a,
    )
    response_b = client.get(
        "/api/v1/organizations/current/usage",
        headers=organization_b,
    )

    assert response_a.status_code == 200
    assert response_b.status_code == 200

    assert response_a.json()["limits"]["documents"] == 10
    assert response_b.json()["limits"]["documents"] is None

    update_b = client.patch(
        "/api/v1/organizations/current/usage-limits",
        headers=organization_b,
        json={"max_documents": 25},
    )

    assert update_b.status_code == 200

    response_a_after = client.get(
        "/api/v1/organizations/current/usage",
        headers=organization_a,
    )

    assert response_a_after.json()["limits"]["documents"] == 10


def test_negative_usage_limits_are_rejected(client):
    headers = register_owner(client, "usage-negative@example.com")

    response = client.patch(
        "/api/v1/organizations/current/usage-limits",
        headers=headers,
        json={"max_documents": -1},
    )

    assert response.status_code == 422


def test_unknown_usage_limit_fields_are_rejected(client):
    headers = register_owner(client, "usage-invalid@example.com")

    response = client.patch(
        "/api/v1/organizations/current/usage-limits",
        headers=headers,
        json={"max_fake_resource": 10},
    )

    assert response.status_code == 422
