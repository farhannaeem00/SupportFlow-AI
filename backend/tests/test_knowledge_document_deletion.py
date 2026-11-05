
import logging
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.models import AuditLog
import app.services.knowledge_document_service as service


@pytest.fixture
def deletion_setup(tmp_path, monkeypatch):
    organization_id = "org-test"
    knowledge_base_id = "kb-test"
    document_id = "doc-test"
    actor_id = "actor-test"

    upload_root = tmp_path / "uploads"
    storage_directory = (
        upload_root / organization_id / knowledge_base_id
    )
    storage_directory.mkdir(parents=True)

    document_file = storage_directory / "document.pdf"
    document_file.write_bytes(b"test document")

    document = SimpleNamespace(
        id=document_id,
        stored_filename="document.pdf",
        content_type="application/pdf",
        file_size=1024,
    )

    db = Mock()
    vector_cleanup = Mock()

    monkeypatch.setattr(service, "get_upload_root", lambda: upload_root)
    monkeypatch.setattr(
        service,
        "get_document",
        lambda *args: document,
    )
    monkeypatch.setattr(
        service,
        "delete_document_chunks",
        vector_cleanup,
    )

    return SimpleNamespace(
        organization_id=organization_id,
        knowledge_base_id=knowledge_base_id,
        document_id=document_id,
        actor_id=actor_id,
        document=document,
        document_file=document_file,
        db=db,
        vector_cleanup=vector_cleanup,
    )


def test_delete_document_removes_database_vectors_and_file(deletion_setup):
    setup = deletion_setup

    service.delete_document(
        setup.db,
        setup.organization_id,
        setup.knowledge_base_id,
        setup.document_id,
        setup.actor_id,
    )

    setup.db.delete.assert_called_once_with(setup.document)
    setup.db.commit.assert_called_once()
    setup.vector_cleanup.assert_called_once_with(
        setup.organization_id,
        setup.document_id,
    )
    assert not setup.document_file.exists()


def test_delete_document_does_not_cleanup_if_database_commit_fails(
    deletion_setup,
):
    setup = deletion_setup
    setup.db.commit.side_effect = RuntimeError("Database commit failed")

    with pytest.raises(RuntimeError, match="Database commit failed"):
        service.delete_document(
            setup.db,
            setup.organization_id,
            setup.knowledge_base_id,
            setup.document_id,
            setup.actor_id,
        )

    setup.db.rollback.assert_called_once()
    setup.vector_cleanup.assert_not_called()
    assert setup.document_file.exists()


def test_delete_document_logs_vector_cleanup_failure(
    deletion_setup,
    caplog,
):
    setup = deletion_setup
    setup.vector_cleanup.side_effect = RuntimeError("ChromaDB unavailable")

    with caplog.at_level(logging.ERROR):
        service.delete_document(
            setup.db,
            setup.organization_id,
            setup.knowledge_base_id,
            setup.document_id,
            setup.actor_id,
        )

    setup.db.commit.assert_called_once()
    assert not setup.document_file.exists()
    assert "Failed to delete vectors" in caplog.text


def test_delete_document_logs_file_cleanup_failure(
    deletion_setup,
    monkeypatch,
    caplog,
):
    setup = deletion_setup

    def fail_unlink(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr(type(setup.document_file), "unlink", fail_unlink)

    with caplog.at_level(logging.ERROR):
        service.delete_document(
            setup.db,
            setup.organization_id,
            setup.knowledge_base_id,
            setup.document_id,
            setup.actor_id,
        )

    setup.db.commit.assert_called_once()
    setup.vector_cleanup.assert_called_once()
    assert "Failed to delete uploaded document file" in caplog.text


def test_delete_document_rejects_unsafe_storage_path(deletion_setup):
    setup = deletion_setup

    setup.document.stored_filename = "../../../outside.pdf"

    outside_file = setup.document_file.parents[2] / "outside.pdf"
    outside_file.write_bytes(b"must not be deleted")

    with pytest.raises(HTTPException) as exc_info:
        service.delete_document(
            setup.db,
            setup.organization_id,
            setup.knowledge_base_id,
            setup.document_id,
            setup.actor_id,
        )

    assert exc_info.value.status_code == 400
    assert outside_file.exists()
    setup.db.delete.assert_not_called()
    setup.db.add.assert_not_called()
    setup.vector_cleanup.assert_not_called()


def test_delete_document_records_audit_log(deletion_setup):
    setup = deletion_setup

    service.delete_document(
        setup.db,
        setup.organization_id,
        setup.knowledge_base_id,
        setup.document_id,
        setup.actor_id,
    )

    audit_log = setup.db.add.call_args.args[0]

    assert isinstance(audit_log, AuditLog)
    assert audit_log.organization_id == setup.organization_id
    assert audit_log.actor_id == setup.actor_id
    assert audit_log.action == "knowledge_document_deleted"
    assert audit_log.resource_type == "knowledge_document"
    assert audit_log.resource_id == setup.document_id
    assert audit_log.details == {
        "knowledge_base_id": setup.knowledge_base_id,
        "content_type": "application/pdf",
        "file_size": 1024,
    }


def test_delete_document_rolls_back_audit_if_commit_fails(
    deletion_setup,
):
    setup = deletion_setup
    setup.db.commit.side_effect = RuntimeError("Database commit failed")

    with pytest.raises(RuntimeError, match="Database commit failed"):
        service.delete_document(
            setup.db,
            setup.organization_id,
            setup.knowledge_base_id,
            setup.document_id,
            setup.actor_id,
        )

    audit_log = setup.db.add.call_args.args[0]

    assert isinstance(audit_log, AuditLog)
    setup.db.rollback.assert_called_once()
    setup.vector_cleanup.assert_not_called()
    assert setup.document_file.exists()
