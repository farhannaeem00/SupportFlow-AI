
from uuid import uuid4

from app.models import KnowledgeBase, KnowledgeDocument

from sqlalchemy import select

from app.models import AuditLog, User


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
    }


def auth_headers(owner):
    return {
        "Authorization": f"Bearer {owner['token']}",
        "X-Organization-ID": owner["organization_id"],
    }


def create_knowledge_base(client, owner, name):
    response = client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers(owner),
        json={
            "name": name,
            "description": f"{name} description",
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def create_test_document(db_session, owner, knowledge_base_id, filename):
    document = KnowledgeDocument(
        organization_id=owner["organization_id"],
        knowledge_base_id=knowledge_base_id,
        uploaded_by=None,
        original_filename=filename,
        stored_filename=f"{uuid4()}.pdf",
        content_type="application/pdf",
        file_size=1024,
        checksum="a" * 64,
        status="processed",
        chunk_count=2,
    )

    db_session.add(document)
    db_session.flush()

    return document


def test_knowledge_base_pagination(client):
    owner = register_owner(client, "kb_pagination@example.com")

    create_knowledge_base(client, owner, "Knowledge Base 1")
    create_knowledge_base(client, owner, "Knowledge Base 2")
    create_knowledge_base(client, owner, "Knowledge Base 3")

    response = client.get(
        "/api/v1/knowledge-bases?skip=0&limit=2",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert len(response.json()) == 2

    response = client.get(
        "/api/v1/knowledge-bases?skip=2&limit=2",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_knowledge_base_pagination_validation(client):
    owner = register_owner(client, "kb_validation@example.com")

    for limit in (0, 101):
        response = client.get(
            f"/api/v1/knowledge-bases?limit={limit}",
            headers=auth_headers(owner),
        )

        assert response.status_code == 422


def test_knowledge_base_document_counts(client, db_session):
    owner = register_owner(client, "kb_counts@example.com")

    first_kb = create_knowledge_base(client, owner, "First KB")
    second_kb = create_knowledge_base(client, owner, "Second KB")

    create_test_document(
        db_session, owner, first_kb["id"], "first-1.pdf"
    )
    create_test_document(
        db_session, owner, first_kb["id"], "first-2.pdf"
    )
    create_test_document(
        db_session, owner, second_kb["id"], "second-1.pdf"
    )

    response = client.get(
        "/api/v1/knowledge-bases",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200

    counts = {
        item["name"]: item["document_count"]
        for item in response.json()
    }

    assert counts["First KB"] == 2
    assert counts["Second KB"] == 1


def test_knowledge_document_pagination(client, db_session):
    owner = register_owner(client, "doc_pagination@example.com")

    knowledge_base = create_knowledge_base(
        client, owner, "Document Pagination KB"
    )

    for index in range(3):
        create_test_document(
            db_session,
            owner,
            knowledge_base["id"],
            f"document-{index}.pdf",
        )

    url = (
        f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents"
    )

    response = client.get(
        f"{url}?skip=0&limit=2",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert len(response.json()) == 2

    response = client.get(
        f"{url}?skip=2&limit=2",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_knowledge_document_pagination_validation(client):
    owner = register_owner(client, "doc_validation@example.com")

    knowledge_base = create_knowledge_base(
        client, owner, "Document Validation KB"
    )

    url = (
        f"/api/v1/knowledge-bases/{knowledge_base['id']}/documents"
    )

    for limit in (0, 101):
        response = client.get(
            f"{url}?limit={limit}",
            headers=auth_headers(owner),
        )

        assert response.status_code == 422


def test_knowledge_base_list_is_organization_scoped(client):
    owner_one = register_owner(client, "kb_tenant_one@example.com")
    owner_two = register_owner(client, "kb_tenant_two@example.com")

    create_knowledge_base(client, owner_one, "Organization One KB")
    create_knowledge_base(client, owner_two, "Organization Two KB")

    response = client.get(
        "/api/v1/knowledge-bases",
        headers=auth_headers(owner_one),
    )

    assert response.status_code == 200

    names = {item["name"] for item in response.json()}

    assert names == {"Organization One KB"}


def test_knowledge_document_list_rejects_another_organizations_kb(
    client,
):
    owner_one = register_owner(client, "doc_tenant_one@example.com")
    owner_two = register_owner(client, "doc_tenant_two@example.com")

    foreign_kb = create_knowledge_base(
        client, owner_two, "Foreign Knowledge Base"
    )

    response = client.get(
        f"/api/v1/knowledge-bases/{foreign_kb['id']}/documents",
        headers=auth_headers(owner_one),
    )

    assert response.status_code == 404


def test_knowledge_base_operations_create_audit_logs(
    client,
    db_session,
    monkeypatch,
):
    import app.services.knowledge_base_service as service

    monkeypatch.setattr(
        service,
        "delete_knowledge_base_chunks",
        lambda *args: None,
    )

    owner = register_owner(client, "kb_audit@example.com")

    owner_user = db_session.scalar(
        select(User).where(User.email == "kb_audit@example.com")
    )

    # Create.
    create_response = client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers(owner),
        json={
            "name": "Audit Test KB",
            "description": "Initial description",
        },
    )

    assert create_response.status_code == 201
    knowledge_base_id = create_response.json()["id"]

    # Update.
    update_response = client.patch(
        f"/api/v1/knowledge-bases/{knowledge_base_id}",
        headers=auth_headers(owner),
        json={"name": "Updated Audit Test KB"},
    )

    assert update_response.status_code == 200

    # Same value must not create another audit record.
    unchanged_response = client.patch(
        f"/api/v1/knowledge-bases/{knowledge_base_id}",
        headers=auth_headers(owner),
        json={"name": "Updated Audit Test KB"},
    )

    assert unchanged_response.status_code == 200

    # Delete.
    delete_response = client.delete(
        f"/api/v1/knowledge-bases/{knowledge_base_id}",
        headers=auth_headers(owner),
    )

    assert delete_response.status_code == 204

    logs = db_session.scalars(
        select(AuditLog)
        .where(
            AuditLog.organization_id == owner["organization_id"],
            AuditLog.resource_id == knowledge_base_id,
        )
        .order_by(AuditLog.created_at.asc())
    ).all()

    assert [log.action for log in logs] == [
        "knowledge_base_created",
        "knowledge_base_updated",
        "knowledge_base_deleted",
    ]

    assert all(
        log.resource_type == "knowledge_base"
        for log in logs
    )

    assert all(
        log.actor_id == owner_user.id
        for log in logs
    )

    assert logs[0].details["name"] == "Audit Test KB"
    assert logs[1].details["updated_fields"] == ["name"]
    assert logs[2].details["name"] == "Updated Audit Test KB"

def set_knowledge_base_limit(client, owner, limit):
    response = client.patch(
        "/api/v1/organizations/current/usage-limits",
        headers=auth_headers(owner),
        json={"max_knowledge_bases": limit},
    )

    assert response.status_code == 200, response.text
    return response


def test_knowledge_base_limit_allows_creation_below_limit(client):
    owner = register_owner(client, "kb_limit_allowed@example.com")

    set_knowledge_base_limit(client, owner, 2)

    first = create_knowledge_base(client, owner, "Allowed KB 1")
    second = create_knowledge_base(client, owner, "Allowed KB 2")

    assert first["id"]
    assert second["id"]


def test_knowledge_base_limit_rejects_creation_at_limit(client):
    owner = register_owner(client, "kb_limit_rejected@example.com")

    set_knowledge_base_limit(client, owner, 1)

    create_knowledge_base(client, owner, "Existing KB")

    response = client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers(owner),
        json={
            "name": "Rejected KB",
            "description": "This must not be created",
        },
    )

    assert response.status_code == 403, response.text
    assert "knowledge_bases" in response.text

    # Increase the limit and retry the same name.
    # This verifies the rejected request did not create the record.
    set_knowledge_base_limit(client, owner, 2)

    retry = create_knowledge_base(client, owner, "Rejected KB")

    assert retry["name"] == "Rejected KB"


def test_knowledge_base_limit_null_allows_unlimited_creation(client):
    owner = register_owner(client, "kb_limit_unlimited@example.com")

    set_knowledge_base_limit(client, owner, 1)

    create_knowledge_base(client, owner, "First KB")

    set_knowledge_base_limit(client, owner, None)

    second = create_knowledge_base(client, owner, "Second KB")

    assert second["name"] == "Second KB"


def test_knowledge_base_limit_is_isolated_between_organizations(client):
    owner_one = register_owner(client, "kb_limit_org_one@example.com")
    owner_two = register_owner(client, "kb_limit_org_two@example.com")

    set_knowledge_base_limit(client, owner_one, 1)

    create_knowledge_base(client, owner_one, "Organization One KB")

    rejected = client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers(owner_one),
        json={
            "name": "Organization One Extra KB",
            "description": "Must be rejected",
        },
    )

    assert rejected.status_code == 403, rejected.text

    # Organization Two has no configured limit.
    created = create_knowledge_base(
        client,
        owner_two,
        "Organization Two KB",
    )

    assert created["name"] == "Organization Two KB"