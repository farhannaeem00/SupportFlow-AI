import hashlib
import uuid
import zipfile

from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KnowledgeBase, KnowledgeDocument
from app.services.knowledge.vector_store import delete_document_chunks


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
MAX_DOCX_TOTAL_UNCOMPRESSED_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_DOCX_ENTRY_SIZE = 20 * 1024 * 1024  # 20 MB
MAX_DOCX_COMPRESSION_RATIO = 200


def get_upload_root() -> Path:
    root = Path(settings.upload_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


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
        import io

        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                entries = archive.infolist()

                if len(entries) > MAX_DOCX_ENTRIES:
                    raise ValueError("Too many DOCX archive entries")

                filenames = {entry.filename for entry in entries}

                if "[Content_Types].xml" not in filenames:
                    raise ValueError("Invalid DOCX structure")

                if "word/document.xml" not in filenames:
                    raise ValueError("Missing document content")

                total_uncompressed_size = 0

                for entry in entries:
                    if entry.is_dir():
                        continue

                    if entry.flag_bits & 0x1:
                        raise ValueError("Encrypted DOCX entries are not supported")

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
                            raise ValueError("Invalid DOCX compression size")

                        compression_ratio = (
                            entry.file_size / entry.compress_size
                        )

                        if compression_ratio > MAX_DOCX_COMPRESSION_RATIO:
                            raise ValueError("Suspicious DOCX compression ratio")

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

    document_id = uuid.uuid4()
    stored_filename = f"{document_id}{extension}"

    storage_directory = (
        get_upload_root()
        / str(organization_id)
        / str(knowledge_base.id)
    )

    storage_directory.mkdir(parents=True, exist_ok=True)

    file_path = storage_directory / stored_filename

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

    try:
        file_path.write_bytes(content)

        db.add(document)
        db.commit()
        db.refresh(document)

    except Exception:
        db.rollback()
        file_path.unlink(missing_ok=True)
        raise

    return document


def list_documents(
    db: Session,
    organization_id: UUID,
    knowledge_base_id: UUID,
) -> list[KnowledgeDocument]:

    get_knowledge_base(db, organization_id, knowledge_base_id)

    statement = (
        select(KnowledgeDocument)
        .where(
            KnowledgeDocument.organization_id == organization_id,
            KnowledgeDocument.knowledge_base_id == knowledge_base_id,
        )
        .order_by(KnowledgeDocument.created_at.desc())
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
) -> None:

    document = get_document(
        db,
        organization_id,
        knowledge_base_id,
        document_id,
    )

    storage_directory = (
        get_upload_root()
        / str(organization_id)
        / str(knowledge_base_id)
    ).resolve()

    file_path = (
        storage_directory / document.stored_filename
    ).resolve()

    if file_path.parent != storage_directory:
        raise HTTPException(
            status_code=400,
            detail="Invalid document storage path",
        )

    # Delete vectors before deleting the database record.
    delete_document_chunks(
        organization_id,
        document_id,
    )

    db.delete(document)
    db.commit()

    file_path.unlink(missing_ok=True)