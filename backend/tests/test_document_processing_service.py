
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.services.knowledge import document_processing_service as service


def test_process_knowledge_document_success(monkeypatch, tmp_path):
    organization_id = uuid4()
    knowledge_base_id = uuid4()
    document_id = uuid4()

    document = SimpleNamespace(
        id=document_id,
        organization_id=organization_id,
        knowledge_base_id=knowledge_base_id,
        stored_filename="document.txt",
        original_filename="document.txt",
        status="pending",
        error_message=None,
        chunk_count=0,
    )

    # Create the uploaded document at its expected storage location.
    document_directory = (
        tmp_path / str(organization_id) / str(knowledge_base_id)
    )
    document_directory.mkdir(parents=True)

    file_path = document_directory / document.stored_filename
    file_path.write_text(
        "Customer support documentation and troubleshooting guide.",
        encoding="utf-8",
    )

    class FakeDB:
        def __init__(self):
            self.commit_count = 0
            self.rollback_count = 0
            self.closed = False

        def scalar(self, statement):
            return document

        def commit(self):
            self.commit_count += 1

        def rollback(self):
            self.rollback_count += 1

        def close(self):
            self.closed = True

    fake_db = FakeDB()

    monkeypatch.setattr(service, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(service.settings, "upload_dir", str(tmp_path))

    deleted_documents = []
    stored_documents = []

    def fake_delete(org_id, doc_id):
        deleted_documents.append((org_id, doc_id))

    def fake_embeddings(chunks):
        assert chunks
        return [[0.1, 0.2, 0.3] for _ in chunks]

    def fake_store_document_chunks(**kwargs):
        stored_documents.append(kwargs)
        return len(kwargs["chunks"])

    monkeypatch.setattr(
        service,
        "delete_document_chunks",
        fake_delete,
    )
    monkeypatch.setattr(
        service,
        "generate_embeddings",
        fake_embeddings,
    )
    monkeypatch.setattr(
        service,
        "store_document_chunks",
        fake_store_document_chunks,
    )

    service.process_knowledge_document(
        organization_id,
        knowledge_base_id,
        document_id,
    )

    assert document.status == "processed"
    assert document.error_message is None
    assert document.chunk_count > 0

    assert len(deleted_documents) == 1
    assert len(stored_documents) == 1

    stored = stored_documents[0]

    assert stored["organization_id"] == organization_id
    assert stored["knowledge_base_id"] == knowledge_base_id
    assert stored["document_id"] == document_id
    assert stored["filename"] == "document.txt"

    assert fake_db.commit_count == 2
    assert fake_db.rollback_count == 0
    assert fake_db.closed is True


def test_process_knowledge_document_handles_extraction_failure(
    monkeypatch,
    tmp_path,
):
    organization_id = uuid4()
    knowledge_base_id = uuid4()
    document_id = uuid4()

    document = SimpleNamespace(
        id=document_id,
        organization_id=organization_id,
        knowledge_base_id=knowledge_base_id,
        stored_filename="document.txt",
        original_filename="document.txt",
        status="pending",
        error_message=None,
        chunk_count=0,
    )

    document_directory = (
        tmp_path / str(organization_id) / str(knowledge_base_id)
    )
    document_directory.mkdir(parents=True)

    (document_directory / "document.txt").write_text(
        "Test document content.",
        encoding="utf-8",
    )

    class FakeDB:
        def __init__(self):
            self.commit_count = 0
            self.rollback_count = 0
            self.closed = False

        def scalar(self, statement):
            return document

        def commit(self):
            self.commit_count += 1

        def rollback(self):
            self.rollback_count += 1

        def close(self):
            self.closed = True

    fake_db = FakeDB()
    deleted_documents = []

    monkeypatch.setattr(service, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(service.settings, "upload_dir", str(tmp_path))

    monkeypatch.setattr(
        service,
        "delete_document_chunks",
        lambda org_id, doc_id: deleted_documents.append(
            (org_id, doc_id)
        ),
    )

    def fail_extraction(filename, content):
        raise ValueError("Simulated extraction failure")

    monkeypatch.setattr(
        service,
        "extract_document_text",
        fail_extraction,
    )

    service.process_knowledge_document(
        organization_id,
        knowledge_base_id,
        document_id,
    )

    assert document.status == "failed"
    assert document.chunk_count == 0
    assert document.error_message == (
        "Document processing failed. Please check the file "
        "and try uploading it again."
    )

    assert len(deleted_documents) == 2
    assert fake_db.commit_count == 2
    assert fake_db.rollback_count == 1
    assert fake_db.closed is True
