
import logging
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

import app.services.knowledge_base_service as service


@pytest.fixture
def deletion_setup(tmp_path, monkeypatch):
    organization_id = "org-test"
    knowledge_base_id = "kb-test"

    upload_root = tmp_path / "uploads"
    kb_directory = (
        upload_root
        / organization_id
        / knowledge_base_id
    )
    kb_directory.mkdir(parents=True)

    document_file = kb_directory / "document.pdf"
    document_file.write_bytes(b"test document")

    document = SimpleNamespace(
        stored_filename="document.pdf",
    )

    knowledge_base = SimpleNamespace(
        id=knowledge_base_id,
        documents=[document],
    )

    db = Mock()
    db.scalar.return_value = knowledge_base

    vector_cleanup = Mock()

    monkeypatch.setattr(service.settings, "upload_dir", str(upload_root))
    monkeypatch.setattr(
        service,
        "delete_knowledge_base_chunks",
        vector_cleanup,
    )

    return SimpleNamespace(
        organization_id=organization_id,
        knowledge_base_id=knowledge_base_id,
        upload_root=upload_root,
        document_file=document_file,
        knowledge_base=knowledge_base,
        db=db,
        vector_cleanup=vector_cleanup,
    )


def test_delete_knowledge_base_removes_database_vectors_and_files(
    deletion_setup,
):
    setup = deletion_setup

    service.delete_knowledge_base(
        setup.db,
        setup.organization_id,
        setup.knowledge_base_id,
    )

    setup.db.delete.assert_called_once_with(setup.knowledge_base)
    setup.db.commit.assert_called_once()

    setup.vector_cleanup.assert_called_once_with(
        setup.organization_id,
        setup.knowledge_base_id,
    )

    assert not setup.document_file.exists()


def test_delete_knowledge_base_does_not_cleanup_if_database_commit_fails(
    deletion_setup,
):
    setup = deletion_setup
    setup.db.commit.side_effect = RuntimeError("Database commit failed")

    with pytest.raises(RuntimeError, match="Database commit failed"):
        service.delete_knowledge_base(
            setup.db,
            setup.organization_id,
            setup.knowledge_base_id,
        )

    setup.vector_cleanup.assert_not_called()
    assert setup.document_file.exists()


def test_delete_knowledge_base_logs_vector_cleanup_failure(
    deletion_setup,
    caplog,
):
    setup = deletion_setup
    setup.vector_cleanup.side_effect = RuntimeError("ChromaDB unavailable")

    with caplog.at_level(logging.ERROR):
        service.delete_knowledge_base(
            setup.db,
            setup.organization_id,
            setup.knowledge_base_id,
        )

    setup.db.commit.assert_called_once()
    assert not setup.document_file.exists()
    assert "Failed to delete vectors" in caplog.text


def test_delete_knowledge_base_logs_file_cleanup_failure(
    deletion_setup,
    monkeypatch,
    caplog,
):
    setup = deletion_setup

    def fail_unlink(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr(
        type(setup.document_file),
        "unlink",
        fail_unlink,
    )

    with caplog.at_level(logging.ERROR):
        service.delete_knowledge_base(
            setup.db,
            setup.organization_id,
            setup.knowledge_base_id,
        )

    setup.db.commit.assert_called_once()
    setup.vector_cleanup.assert_called_once()
    assert "Failed to delete uploaded document file" in caplog.text


def test_delete_knowledge_base_rejects_unsafe_file_path(
    deletion_setup,
    monkeypatch,
    caplog,
):
    setup = deletion_setup

    outside_file = setup.upload_root.parent / "outside.pdf"
    outside_file.write_bytes(b"must not be deleted")

    setup.knowledge_base.documents = [
        SimpleNamespace(
            stored_filename="../../../outside.pdf",
        )
    ]

    with caplog.at_level(logging.ERROR):
        service.delete_knowledge_base(
            setup.db,
            setup.organization_id,
            setup.knowledge_base_id,
        )

    assert outside_file.exists()
    assert "Skipped unsafe document path" in caplog.text
    setup.db.commit.assert_called_once()
    setup.vector_cleanup.assert_called_once()
