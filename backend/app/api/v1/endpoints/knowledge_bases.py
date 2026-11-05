
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_membership, require_roles
from app.models import KnowledgeBase, KnowledgeDocument, OrganizationMember
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
)
from app.services import knowledge_base_service


router = APIRouter(
    prefix="/knowledge-bases",
    tags=["Knowledge Bases"],
)


def build_response(
    db: Session,
    knowledge_base: KnowledgeBase,
) -> KnowledgeBaseResponse:
    document_count = db.scalar(
        select(func.count(KnowledgeDocument.id)).where(
            KnowledgeDocument.knowledge_base_id == knowledge_base.id,
            KnowledgeDocument.organization_id == knowledge_base.organization_id,
        )
    ) or 0

    return KnowledgeBaseResponse(
        **{
            column.name: getattr(knowledge_base, column.name)
            for column in KnowledgeBase.__table__.columns
        },
        document_count=document_count,
    )


def build_list_responses(
    db: Session,
    organization_id: UUID,
    knowledge_bases: list[KnowledgeBase],
) -> list[KnowledgeBaseResponse]:
    if not knowledge_bases:
        return []

    knowledge_base_ids = [item.id for item in knowledge_bases]

    count_rows = db.execute(
        select(
            KnowledgeDocument.knowledge_base_id,
            func.count(KnowledgeDocument.id),
        )
        .where(
            KnowledgeDocument.organization_id == organization_id,
            KnowledgeDocument.knowledge_base_id.in_(knowledge_base_ids),
        )
        .group_by(KnowledgeDocument.knowledge_base_id)
    ).all()

    document_counts = dict(count_rows)

    return [
        KnowledgeBaseResponse(
            **{
                column.name: getattr(item, column.name)
                for column in KnowledgeBase.__table__.columns
            },
            document_count=document_counts.get(item.id, 0),
        )
        for item in knowledge_bases
    ]


@router.post(
    "",
    response_model=KnowledgeBaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_knowledge_base(
    data: KnowledgeBaseCreate,
    membership: OrganizationMember = Depends(
        require_roles("owner", "admin")
    ),
    db: Session = Depends(get_db),
):
    knowledge_base = knowledge_base_service.create_knowledge_base(
        db,
        membership.organization_id,
        membership.user_id,
        data,
    )

    return build_response(db, knowledge_base)


@router.get(
    "",
    response_model=list[KnowledgeBaseResponse],
)
def list_knowledge_bases(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    membership: OrganizationMember = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    knowledge_bases = knowledge_base_service.list_knowledge_bases(
        db,
        membership.organization_id,
        skip=skip,
        limit=limit,
    )

    return build_list_responses(
        db,
        membership.organization_id,
        knowledge_bases,
    )


@router.get(
    "/{knowledge_base_id}",
    response_model=KnowledgeBaseResponse,
)
def get_knowledge_base(
    knowledge_base_id: UUID,
    membership: OrganizationMember = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    knowledge_base = knowledge_base_service.get_knowledge_base(
        db,
        membership.organization_id,
        knowledge_base_id,
    )

    return build_response(db, knowledge_base)


@router.patch(
    "/{knowledge_base_id}",
    response_model=KnowledgeBaseResponse,
)
def update_knowledge_base(
    knowledge_base_id: UUID,
    data: KnowledgeBaseUpdate,
    membership: OrganizationMember = Depends(
        require_roles("owner", "admin")
    ),
    db: Session = Depends(get_db),
):
    knowledge_base = knowledge_base_service.update_knowledge_base(
        db,
        membership.organization_id,
        knowledge_base_id,
        membership.user_id,
        data,
    )

    return build_response(db, knowledge_base)


@router.delete(
    "/{knowledge_base_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_knowledge_base(
    knowledge_base_id: UUID,
    membership: OrganizationMember = Depends(
        require_roles("owner", "admin")
    ),
    db: Session = Depends(get_db),
):
    knowledge_base_service.delete_knowledge_base(
        db,
        membership.organization_id,
        knowledge_base_id,
        membership.user_id,
    )
