
import logging
from pathlib import Path
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import KnowledgeDocument
from app.services.knowledge.document_processor import (
    extract_document_text,
    chunk_text,
)
from app.services.knowledge.embedding_service import generate_embeddings
from app.services.knowledge.vector_store import (
    store_document_chunks,
    delete_document_chunks,
)


logger = logging.getLogger(__name__)

PROCESSABLE_STATUSES = {"uploaded", "failed"}


def get_document_path(document: KnowledgeDocument) -> Path:
    """Build the document's storage path safely."""

    upload_root = Path(settings.upload_dir).resolve()

    document_directory = (
        upload_root
        / str(document.organization_id)
        / str(document.knowledge_base_id)
    ).resolve()

    file_path = (
        document_directory / document.stored_filename
    ).resolve()

    if file_path.parent != document_directory:
        raise ValueError("Invalid document storage path")

    return file_path


def _claim_document(
    db,
    organization_id: UUID,
    knowledge_base_id: UUID,
    document_id: UUID,
):
    """
    Atomically claim an uploaded or failed document.

    PostgreSQL row locking prevents concurrent workers from
    claiming the same document.
    """

    document = db.scalar(
        select(KnowledgeDocument)
        .where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.organization_id == organization_id,
            KnowledgeDocument.knowledge_base_id == knowledge_base_id,
        )
        .with_for_update()
    )

    if not document:
        db.rollback()
        return None

    if document.status not in PROCESSABLE_STATUSES:
        db.rollback()
        return None

    document.status = "processing"
    document.processing_started_at = datetime.now(timezone.utc)
    document.error_message = None
    document.chunk_count = 0

    db.commit()

    return document


def process_knowledge_document(
    organization_id: UUID,
    knowledge_base_id: UUID,
    document_id: UUID,
) -> None:
    """
    Extract, chunk, embed and store an uploaded document.

    Uses its own database session because this runs in a background task.
    Only one worker can claim a document at a time.
    """

    db = SessionLocal()

    try:
        document = _claim_document(
            db,
            organization_id,
            knowledge_base_id,
            document_id,
        )

        if document is None:
            logger.info(
                "Document %s was not claimed; it may already be processing "
                "or completed.",
                document_id,
            )
            return

        # Remove previous partial processing results.
        delete_document_chunks(
            organization_id,
            document_id,
        )

        file_path = get_document_path(document)

        if not file_path.is_file():
            raise FileNotFoundError(
                "Uploaded document file was not found"
            )

        extracted_text = extract_document_text(
            str(file_path),
            file_path.read_bytes(),
        )

        if not extracted_text or not extracted_text.strip():
            raise ValueError(
                "No readable text was found in the document"
            )

        chunks = chunk_text(extracted_text)

        if not chunks:
            raise ValueError(
                "Document did not produce any text chunks"
            )

        embeddings = generate_embeddings(chunks)

        if len(embeddings) != len(chunks):
            raise ValueError(
                "Generated embedding count does not match chunk count"
            )

        chunk_count = store_document_chunks(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            chunks=chunks,
            embeddings=embeddings,
            filename=document.original_filename,
        )

        if chunk_count != len(chunks):
            raise ValueError(
                "Not all document chunks were stored"
            )

        document.chunk_count = chunk_count
        document.status = "processed"
        document.processing_started_at = None
        document.error_message = None

        db.commit()

        logger.info(
            "Document %s processed successfully with %s chunks.",
            document_id,
            chunk_count,
        )

    except Exception:
        db.rollback()

        logger.exception(
            "Document processing failed for document %s.",
            document_id,
        )

        # Remove partially stored vectors.
        try:
            delete_document_chunks(
                organization_id,
                document_id,
            )
        except Exception:
            logger.exception(
                "Failed to clean up vectors for document %s.",
                document_id,
            )

        # Record failure in a separate transaction.
        try:
            failed_document = db.scalar(
                select(KnowledgeDocument)
                .where(
                    KnowledgeDocument.id == document_id,
                    KnowledgeDocument.organization_id == organization_id,
                    KnowledgeDocument.knowledge_base_id == knowledge_base_id,
                )
                .with_for_update()
            )

            if failed_document and failed_document.status == "processing":
                failed_document.status = "failed"
                failed_document.processing_started_at = None
                failed_document.error_message = (
                    "Document processing failed. Please check the file "
                    "and try again."
                )

                db.commit()
            else:
                db.rollback()

        except Exception:
            db.rollback()
            logger.exception(
                "Failed to record processing failure for document %s.",
                document_id,
            )

    finally:
        db.close()
