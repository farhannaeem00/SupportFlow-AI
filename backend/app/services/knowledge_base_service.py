from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import KnowledgeBase, KnowledgeDocument
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
)


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

    db.delete(knowledge_base)
    db.commit()