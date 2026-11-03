
import logging
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KnowledgeBase
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
)
from app.services.knowledge.vector_store import (
    delete_knowledge_base_chunks,
)
logger = logging.getLogger(__name__)

def create_knowledge_base(
    db: Session,
    organization_id: UUID,
    data: KnowledgeBaseCreate,
) -> KnowledgeBase:

    knowledge_base = KnowledgeBase(
        organization_id=organization_id,
        name=data.name.strip(),
        description=data.description,
    )

    if not knowledge_base.name:
        raise HTTPException(
            status_code=422,
            detail="Knowledge base name cannot be empty",
        )

    db.add(knowledge_base)

    try:
        db.commit()
        db.refresh(knowledge_base)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A knowledge base with this name already exists",
        )

    return knowledge_base


def list_knowledge_bases(
    db: Session,
    organization_id: UUID,
) -> list[KnowledgeBase]:

    statement = (
        select(KnowledgeBase)
        .where(KnowledgeBase.organization_id == organization_id)
        .order_by(KnowledgeBase.created_at.desc())
    )

    return list(db.scalars(statement).all())


def get_knowledge_base(
    db: Session,
    organization_id: UUID,
    knowledge_base_id: UUID,
) -> KnowledgeBase:

    knowledge_base = db.scalar(
        select(KnowledgeBase).where(
            KnowledgeBase.id == knowledge_base_id,
            KnowledgeBase.organization_id == organization_id,
        )
    )

    if not knowledge_base:
        raise HTTPException(
            status_code=404,
            detail="Knowledge base not found",
        )

    return knowledge_base


def update_knowledge_base(
    db: Session,
    organization_id: UUID,
    knowledge_base_id: UUID,
    data: KnowledgeBaseUpdate,
) -> KnowledgeBase:

    knowledge_base = get_knowledge_base(
        db,
        organization_id,
        knowledge_base_id,
    )

    updates = data.model_dump(exclude_unset=True)

    if "name" in updates:
        updates["name"] = updates["name"].strip()

        if not updates["name"]:
            raise HTTPException(
                status_code=422,
                detail="Knowledge base name cannot be empty",
            )

    for field, value in updates.items():
        setattr(knowledge_base, field, value)

    try:
        db.commit()
        db.refresh(knowledge_base)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A knowledge base with this name already exists",
        )

    return knowledge_base


def delete_knowledge_base(
    db: Session,
    organization_id: UUID,
    knowledge_base_id: UUID,
) -> None:

    knowledge_base = get_knowledge_base(
        db,
        organization_id,
        knowledge_base_id,
    )

    documents = list(knowledge_base.documents)

    upload_root = Path(settings.upload_dir).resolve()
    document_paths = []

    for document in documents:
        document_path = (
            upload_root
            / str(organization_id)
            / str(knowledge_base_id)
            / document.stored_filename
        ).resolve()

        if not document_path.is_relative_to(upload_root):
            logger.error(
                "Skipped unsafe document path during knowledge base deletion: %s",
                document_path,
            )
            continue

        document_paths.append(document_path)

    # Commit database deletion before external cleanup.
    try:
        db.delete(knowledge_base)
        db.commit()
    except Exception:
        db.rollback()
        raise

    # Remove knowledge base vectors.
    try:
        delete_knowledge_base_chunks(
            organization_id,
            knowledge_base_id,
        )
    except Exception:
        logger.exception(
            "Failed to delete vectors for knowledge base %s",
            knowledge_base_id,
        )

    # Remove uploaded document files.
    for document_path in document_paths:
        try:
            document_path.unlink(missing_ok=True)
        except OSError:
            logger.exception(
                "Failed to delete uploaded document file: %s",
                document_path,
            )
