
import uuid
from datetime import datetime, timedelta, timezone

from app.models import Organization, KnowledgeBase, KnowledgeDocument
from app.services.knowledge import document_recovery_service as service


def create_test_document(db_session, status, processing_started_at=None):
    organization = Organization(
        name=f"Recovery Org {uuid.uuid4().hex[:8]}",
        slug=f"recovery-{uuid.uuid4().hex[:12]}",
    )
    db_session.add(organization)
    db_session.flush()

    knowledge_base = KnowledgeBase(
        organization_id=organization.id,
        name="Recovery Test Knowledge Base",
    )
    db_session.add(knowledge_base)
    db_session.flush()

    document = KnowledgeDocument(
        organization_id=organization.id,
        knowledge_base_id=knowledge_base.id,
        uploaded_by=None,
        original_filename="recovery-test.txt",
        stored_filename=f"{uuid.uuid4()}.txt",
        content_type="text/plain",
        file_size=100,
        checksum=uuid.uuid4().hex + uuid.uuid4().hex[:32],
        status=status,
        processing_started_at=processing_started_at,
        chunk_count=5 if status == "processing" else 0,
    )

    db_session.add(document)
    db_session.flush()

    return document


def test_recovers_stale_processing_document(db_session, monkeypatch):
    monkeypatch.setattr(
        service.settings,
        "document_processing_timeout_minutes",
        30,
    )

    stale_time = datetime.now(timezone.utc) - timedelta(minutes=45)

    document = create_test_document(
        db_session,
        status="processing",
        processing_started_at=stale_time,
    )
    document_id = document.id

    recovered_count = service.recover_stale_documents(db_session)

    db_session.refresh(document)

    assert recovered_count == 1
    assert document.status == "uploaded"
    assert document.processing_started_at is None
    assert document.chunk_count == 0
    assert document.error_message is not None


def test_does_not_recover_recent_processing_document(
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        service.settings,
        "document_processing_timeout_minutes",
        30,
    )

    recent_time = datetime.now(timezone.utc) - timedelta(minutes=5)

    document = create_test_document(
        db_session,
        status="processing",
        processing_started_at=recent_time,
    )

    recovered_count = service.recover_stale_documents(db_session)

    db_session.refresh(document)

    assert recovered_count == 0
    assert document.status == "processing"
    assert document.processing_started_at is not None


def test_does_not_recover_document_without_processing_timestamp(
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(
        service.settings,
        "document_processing_timeout_minutes",
        30,
    )

    document = create_test_document(
        db_session,
        status="processing",
        processing_started_at=None,
    )

    recovered_count = service.recover_stale_documents(db_session)

    db_session.refresh(document)

    assert recovered_count == 0
    assert document.status == "processing"
    assert document.processing_started_at is None


def test_does_not_modify_processed_document(db_session, monkeypatch):
    monkeypatch.setattr(
        service.settings,
        "document_processing_timeout_minutes",
        30,
    )

    old_time = datetime.now(timezone.utc) - timedelta(hours=2)

    document = create_test_document(
        db_session,
        status="processed",
        processing_started_at=old_time,
    )

    recovered_count = service.recover_stale_documents(db_session)

    db_session.refresh(document)

    assert recovered_count == 0
    assert document.status == "processed"
    assert document.processing_started_at == old_time
