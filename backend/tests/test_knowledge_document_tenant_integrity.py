
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Organization, KnowledgeBase, KnowledgeDocument


def create_organization(db_session, name):
    organization = Organization(
        name=name,
        slug=f"{name.lower()}-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(organization)
    db_session.flush()
    return organization


def create_knowledge_base(db_session, organization_id, name):
    knowledge_base = KnowledgeBase(
        organization_id=organization_id,
        name=name,
    )
    db_session.add(knowledge_base)
    db_session.flush()
    return knowledge_base


def create_document(organization_id, knowledge_base_id):
    return KnowledgeDocument(
        organization_id=organization_id,
        knowledge_base_id=knowledge_base_id,
        uploaded_by=None,
        original_filename="test.txt",
        stored_filename=f"{uuid.uuid4()}.txt",
        content_type="text/plain",
        file_size=12,
        checksum=uuid.uuid4().hex + uuid.uuid4().hex[:32],
        status="uploaded",
    )


def test_document_cannot_reference_another_organizations_knowledge_base(
    db_session,
):
    organization_a = create_organization(db_session, "Tenant A")
    organization_b = create_organization(db_session, "Tenant B")

    knowledge_base_b = create_knowledge_base(
        db_session,
        organization_b.id,
        "Tenant B Knowledge Base",
    )

    invalid_document = create_document(
        organization_id=organization_a.id,
        knowledge_base_id=knowledge_base_b.id,
    )

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.add(invalid_document)
            db_session.flush()


def test_document_can_reference_its_own_organizations_knowledge_base(
    db_session,
):
    organization = create_organization(db_session, "Valid Tenant")

    knowledge_base = create_knowledge_base(
        db_session,
        organization.id,
        "Valid Knowledge Base",
    )

    document = create_document(
        organization_id=organization.id,
        knowledge_base_id=knowledge_base.id,
    )

    db_session.add(document)
    db_session.flush()

    assert document.id is not None
    assert document.organization_id == organization.id
    assert document.knowledge_base_id == knowledge_base.id
