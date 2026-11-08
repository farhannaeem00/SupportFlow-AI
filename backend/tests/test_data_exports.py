
import io
import json
import zipfile

from app.api.v1.endpoints.exports import CSV_FIELDS


def register_owner(client, email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Export Owner",
            "email": email,
            "password": "OwnerPassword123!",
            "organization_name": "Export Test Organization",
        },
    )

    assert response.status_code == 201, response.text

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


def test_owner_can_export_organization_json(client):
    owner = register_owner(client, "export-json@example.com")

    response = client.get(
        "/api/v1/exports/json",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment" in response.headers["content-disposition"]

    data = response.json()

    assert data["export_version"] == 1
    assert data["organization"]["id"] == owner["organization_id"]
    assert data["organization"]["name"] == "Export Test Organization"

    expected_datasets = {
        "team_members",
        "customers",
        "conversations",
        "messages",
        "conversation_events",
        "ai_insights",
        "knowledge_bases",
        "knowledge_documents",
        "audit_logs",
    }

    assert set(data["data"]) == expected_datasets
    assert len(data["data"]["team_members"]) == 1
    assert data["data"]["team_members"][0]["email"] == (
        "export-json@example.com"
    )

    # Reserved AI operations are internal accounting data.
    assert "monthly_ai_operations_reserved" not in data["usage"]
    assert "ai_operations_reserved" not in data["usage"]


def test_owner_can_export_csv_zip(client):
    owner = register_owner(client, "export-csv@example.com")

    response = client.get(
        "/api/v1/exports/csv",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/zip"
    assert "attachment" in response.headers["content-disposition"]

    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = set(archive.namelist())

        expected_files = {
            "organization.csv",
            "usage.csv",
            "usage_limits.csv",
            "team_members.csv",
            "customers.csv",
            "conversations.csv",
            "messages.csv",
            "conversation_events.csv",
            "ai_insights.csv",
            "knowledge_bases.csv",
            "knowledge_documents.csv",
            "audit_logs.csv",
        }

        assert names == expected_files

        team_csv = archive.read("team_members.csv").decode("utf-8-sig")
        assert "export-csv@example.com" in team_csv

        # Empty datasets must still contain their defined CSV headers.
        customers_csv = archive.read("customers.csv").decode("utf-8-sig")
        assert "full_name" in customers_csv
        assert "email" in customers_csv

        # Verify the CSV header mapping remains complete.
        for dataset_name, fields in CSV_FIELDS.items():
            csv_content = archive.read(f"{dataset_name}.csv").decode(
                "utf-8-sig"
            )
            assert csv_content.splitlines()[0] == ",".join(fields)


def test_agent_cannot_export_organization_data(client):
    owner = register_owner(client, "export-agent-owner@example.com")

    invite_response = client.post(
        "/api/v1/team/members",
        headers=auth_headers(owner),
        json={
            "full_name": "Export Agent",
            "email": "export-agent@example.com",
            "password": "AgentPassword123!",
            "role": "agent",
        },
    )

    assert invite_response.status_code == 201, invite_response.text

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "export-agent@example.com",
            "password": "AgentPassword123!",
        },
    )

    assert login_response.status_code == 200, login_response.text

    agent_headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        ),
        "X-Organization-ID": owner["organization_id"],
    }

    json_response = client.get(
        "/api/v1/exports/json",
        headers=agent_headers,
    )
    csv_response = client.get(
        "/api/v1/exports/csv",
        headers=agent_headers,
    )

    assert json_response.status_code == 403
    assert csv_response.status_code == 403


def test_organization_exports_are_tenant_isolated(client):
    owner_a = register_owner(client, "export-tenant-a@example.com")
    owner_b = register_owner(client, "export-tenant-b@example.com")

    response_a = client.get(
        "/api/v1/exports/json",
        headers=auth_headers(owner_a),
    )
    response_b = client.get(
        "/api/v1/exports/json",
        headers=auth_headers(owner_b),
    )

    assert response_a.status_code == 200, response_a.text
    assert response_b.status_code == 200, response_b.text

    export_a = response_a.json()
    export_b = response_b.json()

    assert export_a["organization"]["id"] == owner_a["organization_id"]
    assert export_b["organization"]["id"] == owner_b["organization_id"]

    emails_a = {
        member["email"]
        for member in export_a["data"]["team_members"]
    }
    emails_b = {
        member["email"]
        for member in export_b["data"]["team_members"]
    }

    assert emails_a == {"export-tenant-a@example.com"}
    assert emails_b == {"export-tenant-b@example.com"}

    assert "export-tenant-b@example.com" not in json.dumps(export_a)
    assert "export-tenant-a@example.com" not in json.dumps(export_b)


def test_export_requires_authentication_and_organization(client):
    for path in (
        "/api/v1/exports/json",
        "/api/v1/exports/csv",
    ):
        response = client.get(path)
        assert response.status_code == 401

    owner = register_owner(client, "export-no-org@example.com")

    response = client.get(
        "/api/v1/exports/json",
        headers={
            "Authorization": f"Bearer {owner['token']}",
        },
    )

    assert response.status_code in (400, 403, 422)
