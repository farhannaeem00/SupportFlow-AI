
import hashlib
import io
import logging
import uuid
import zipfile
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KnowledgeBase, KnowledgeDocument
from app.services.audit_log_service import record_audit_log
from app.services.knowledge.vector_store import delete_document_chunks
from app.services.organization_usage_service import (
    enforce_usage_limit,
    get_current_usage,
    lock_organization,
)

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": (
        "application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    ),
    ".txt": "text/plain",
}

# DOCX archive security limits
MAX_DOCX_ENTRIES = 1000
MAX_DOCX_TOTAL_UNCOMPRESSED_SIZE = 50 * 1024 * 1024
MAX_DOCX_ENTRY_SIZE = 20 * 1024 * 1024
MAX_DOCX_COMPRESSION_RATIO = 200


def get_upload_root() -> Path:
    root = Path(settings.upload_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_document_storage_directory(
    organization_id: UUID,
    knowledge_base_id: UUID,
) -> Path:
    """Return a tenant-scoped directory safely inside the upload root."""

    upload_root = get_upload_root()

    storage_directory = (
        upload_root / str(organization_id) / str(knowledge_base_id)
    ).resolve()

    try:
        storage_directory.relative_to(upload_root)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid document storage directory.",
        )

    return storage_directory


def get_stored_document_path(
    organization_id: UUID,
    knowledge_base_id: UUID,
    stored_filename: str,
) -> Path:
    """Resolve a stored filename without allowing directory traversal."""

    if (
        not stored_filename
        or Path(stored_filename).name != stored_filename
        or "/" in stored_filename
        or "\\" in stored_filename
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid document storage filename.",
        )

    storage_directory = get_document_storage_directory(
        organization_id,
        knowledge_base_id,
    )

    file_path = (storage_directory / stored_filename).resolve()

    if file_path.parent != storage_directory:
        raise HTTPException(
            status_code=400,
            detail="Invalid document storage path.",
        )

    return file_path


def get_knowledge_base(
    db: Session,
    organization_id: UUID,
    knowledge_base_id: UUID,
) -> KnowledgeBase:
    knowledge_base = db.scalar(
        select(KnowledgeBase).where(
            KnowledgeBase.id == knowledge_base_id,
            KnowledgeBase.organization_id == organization_id,
            KnowledgeBase.is_active.is_(True),
        )
    )

    if not knowledge_base:
        raise HTTPException(
            status_code=404,
            detail="Active knowledge base not found",
        )

    return knowledge_base


def validate_file(
    filename: str,
    content: bytes,
) -> tuple[str, str]:
    extension = Path(filename).suffix.lower()

    configured_extensions = {
        item.strip().lower()
        for item in settings.allowed_document_extensions.split(",")
        if item.strip()
    }

    allowed_extensions = ALLOWED_EXTENSIONS & configured_extensions

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=415,
            detail="Only PDF, DOCX, and TXT files are supported",
        )

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty",
        )

    if extension == ".pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF file",
        )

    if extension == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                entries = archive.infolist()

                if len(entries) > MAX_DOCX_ENTRIES:
                    raise ValueError("Too many DOCX archive entries")

                filenames = set()

                for entry in entries:
                    entry_name = entry.orig_filename

                    # Reject empty names, absolute paths and Windows paths.
                    if (
                        not entry_name
                        or "\\" in entry_name
                        or entry_name.startswith("/")
                    ):
                        raise ValueError("Unsafe DOCX archive path")

                    # Permit directory entries ending in "/", but validate
                    # every actual path component.
                    normalized_name = entry_name.rstrip("/")

                    if not normalized_name:
                        raise ValueError("Unsafe DOCX archive path")

                    path_parts = normalized_name.split("/")

                    if any(
                        part in {"", ".", ".."}
                        for part in path_parts
                    ):
                        raise ValueError("Unsafe DOCX archive path")

                    if entry_name in filenames:
                        raise ValueError("Duplicate DOCX archive entry")

                    filenames.add(entry_name)

                if "[Content_Types].xml" not in filenames:
                    raise ValueError("Invalid DOCX structure")

                if "word/document.xml" not in filenames:
                    raise ValueError("Missing document content")

                total_uncompressed_size = 0

                for entry in entries:
                    if entry.is_dir():
                        continue

                    if entry.flag_bits & 0x1:
                        raise ValueError(
                            "Encrypted DOCX entries are not supported"
                        )

                    if entry.file_size > MAX_DOCX_ENTRY_SIZE:
                        raise ValueError("DOCX archive entry is too large")

                    total_uncompressed_size += entry.file_size

                    if (
                        total_uncompressed_size
                        > MAX_DOCX_TOTAL_UNCOMPRESSED_SIZE
                    ):
                        raise ValueError("DOCX archive is too large")

                    if entry.file_size > 0:
                        if entry.compress_size == 0:
                            raise ValueError(
                                "Invalid DOCX compression size"
                            )

                        compression_ratio = (
                            entry.file_size / entry.compress_size
                        )

                        if compression_ratio > MAX_DOCX_COMPRESSION_RATIO:
                            raise ValueError(
                                "Suspicious DOCX compression ratio"
                            )

        except (
            zipfile.BadZipFile,
            ValueError,
            OSError,
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid or unsafe DOCX file",
            )

    if extension == ".txt":
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="TXT files must use UTF-8 encoding",
            )

    return extension, CONTENT_TYPES[extension]


async def upload_document(
    db: Session,
    organization_id: UUID,
    knowledge_base_id: UUID,
    user_id: UUID,
    file: UploadFile,
) -> KnowledgeDocument:
    knowledge_base = get_knowledge_base(
        db,
        organization_id,
        knowledge_base_id,
    )

    original_filename = Path(file.filename or "").name.strip()

    if not original_filename or len(original_filename) > 255:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename",
        )

    max_size = settings.max_upload_size_mb * 1024 * 1024

    content = await file.read(max_size + 1)

    if len(content) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"Maximum upload size is {settings.max_upload_size_mb} MB",
        )

    extension, content_type = validate_file(
        original_filename,
        content,
    )

    checksum = hashlib.sha256(content).hexdigest()

    # Serialize uploads within this organization. This ensures that
    # concurrent uploads cannot both consume the same remaining quota.
    lock_organization(db, organization_id)

    try:
        duplicate = db.scalar(
            select(KnowledgeDocument).where(
                KnowledgeDocument.organization_id == organization_id,
                KnowledgeDocument.knowledge_base_id == knowledge_base.id,
                KnowledgeDocument.checksum == checksum,
            )
        )

        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="This document already exists in the knowledge base",
            )

        current_usage = get_current_usage(db, organization_id)

        # Enforce the maximum number of documents.
        enforce_usage_limit(
            db,
            organization_id,
            metric="documents",
            current_usage=current_usage["documents"],
        )

        # Enforce total storage using the actual uploaded file size.
        enforce_usage_limit(
            db,
            organization_id,
            metric="storage_bytes",
            current_usage=current_usage["storage_bytes"],
            increment=len(content),
        )

    except Exception:
        db.rollback()
        raise

    file_path = None

    try:
        document_id = uuid.uuid4()
        stored_filename = f"{document_id}{extension}"

        storage_directory = get_document_storage_directory(
            organization_id,
            knowledge_base.id,
        )
        storage_directory.mkdir(parents=True, exist_ok=True)

        file_path = get_stored_document_path(
            organization_id,
            knowledge_base.id,
            stored_filename,
        )

        document = KnowledgeDocument(
            id=document_id,
            organization_id=organization_id,
            knowledge_base_id=knowledge_base.id,
            uploaded_by=user_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            content_type=content_type,
            file_size=len(content),
            checksum=checksum,
            status="uploaded",
        )

        file_path.write_bytes(content)

        db.add(document)
        record_audit_log(
            db,
            organization_id=organization_id,
            actor_id=user_id,
            action="knowledge_document_uploaded",
            resource_type="knowledge_document",
            resource_id=document.id,
            details={
                "knowledge_base_id": str(knowledge_base.id),
                "content_type": content_type,
                "file_size": len(content),
            },
        )

        db.commit()
        db.refresh(document)

    except Exception:
        db.rollback()

        if file_path is not None:
            try:
                file_path.unlink(missing_ok=True)
            except OSError:
                logger.exception(
                    "Failed to remove uploaded file after database failure: %s",
                    file_path,
                )

        raise

    return document


def list_documents(
    db: Session,
    organization_id: UUID,
    knowledge_base_id: UUID,
    skip: int = 0,
    limit: int = 20,
) -> list[KnowledgeDocument]:

    get_knowledge_base(
        db,
        organization_id,
        knowledge_base_id,
    )

    statement = (
        select(KnowledgeDocument)
        .where(
            KnowledgeDocument.organization_id == organization_id,
            KnowledgeDocument.knowledge_base_id == knowledge_base_id,
        )
        .order_by(
            KnowledgeDocument.created_at.desc(),
            KnowledgeDocument.id.desc(),
        )
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def get_document(
    db: Session,
    organization_id: UUID,
    knowledge_base_id: UUID,
    document_id: UUID,
) -> KnowledgeDocument:
    get_knowledge_base(db, organization_id, knowledge_base_id)

    document = db.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.organization_id == organization_id,
            KnowledgeDocument.knowledge_base_id == knowledge_base_id,
        )
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    return document


def delete_document(
    db: Session,
    organization_id: UUID,
    knowledge_base_id: UUID,
    document_id: UUID,
    actor_id: UUID,
) -> dict[str, str]:
    document = get_document(
        db,
        organization_id,
        knowledge_base_id,
        document_id,
    )

    file_path = get_stored_document_path(
        organization_id,
        knowledge_base_id,
        document.stored_filename,
    )

    # Record the audit event in the same transaction as deletion.
    try:
        record_audit_log(
            db,
            organization_id=organization_id,
            actor_id=actor_id,
            action="knowledge_document_deleted",
            resource_type="knowledge_document",
            resource_id=document.id,
            details={
                "knowledge_base_id": str(knowledge_base_id),
                "content_type": document.content_type,
                "file_size": document.file_size,
            },
        )

        db.delete(document)
        db.commit()
    except Exception:
        db.rollback()
        raise

    # Vector cleanup is best-effort.
    try:
        delete_document_chunks(
            organization_id,
            document_id,
        )
    except Exception:
        logger.exception(
            "Failed to delete vectors for document %s in organization %s",
            document_id,
            organization_id,
        )

    # File cleanup is also best-effort.
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        logger.exception(
            "Failed to delete uploaded document file: %s",
            file_path,
        )

    return {"message": "Document deleted successfully."}
