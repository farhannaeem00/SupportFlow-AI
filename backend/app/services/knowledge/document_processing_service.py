
from pathlib import Path
from uuid import UUID

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


def process_knowledge_document(
    organization_id: UUID,
    knowledge_base_id: UUID,
    document_id: UUID,
) -> None:
    """
    Extract, chunk, embed and store an uploaded document.

    Uses its own database session because this runs in a background task.
    """

    db = SessionLocal()

    try:
        document = db.scalar(
            select(KnowledgeDocument).where(
                KnowledgeDocument.id == document_id,
                KnowledgeDocument.organization_id == organization_id,
                KnowledgeDocument.knowledge_base_id == knowledge_base_id,
            )
        )

        if not document:
            return

        document.status = "processing"
        document.error_message = None
        document.chunk_count = 0
        db.commit()

        # Remove any previous partial processing results.
        delete_document_chunks(organization_id, document_id)

        file_path = get_document_path(document)

        if not file_path.is_file():
            raise FileNotFoundError("Uploaded document file was not found")

        extracted_text = extract_document_text(
        str(file_path),
        file_path.read_bytes(),
    )

        if not extracted_text or not extracted_text.strip():
            raise ValueError("No readable text was found in the document")

        chunks = chunk_text(extracted_text)

        if not chunks:
            raise ValueError("Document did not produce any text chunks")

        embeddings = generate_embeddings(chunks)

        chunk_count = store_document_chunks(
            organization_id=organization_id,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            chunks=chunks,
            embeddings=embeddings,
            filename=document.original_filename,
        )

        if chunk_count == 0:
            raise ValueError("No document chunks were stored")

        document.chunk_count = chunk_count
        document.status = "processed"
        document.error_message = None

        db.commit()

    except Exception:
        db.rollback()

        # Remove partially stored vectors if processing failed.
        try:
            delete_document_chunks(organization_id, document_id)
        except Exception:
            pass

        # Record failure without exposing internal exception details.
        failed_document = db.scalar(
            select(KnowledgeDocument).where(
                KnowledgeDocument.id == document_id,
                KnowledgeDocument.organization_id == organization_id,
                KnowledgeDocument.knowledge_base_id == knowledge_base_id,
            )
        )

        if failed_document:
            failed_document.status = "failed"
            failed_document.chunk_count = 0
            failed_document.error_message = (
                "Document processing failed. Please check the file "
                "and try uploading it again."
            )
            db.commit()

    finally:
        db.close()
    