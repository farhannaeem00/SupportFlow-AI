
from uuid import uuid4

from app.models import KnowledgeBase, KnowledgeDocument


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
