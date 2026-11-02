
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_membership
from app.models import OrganizationMember
from app.schemas.knowledge_retrieval import (
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.services.knowledge.retrieval_service import (
    retrieve_knowledge,
)


router = APIRouter(
    prefix="/knowledge-bases/{knowledge_base_id}/search",
    tags=["Knowledge Search"],
)


@router.post(
    "",
    response_model=KnowledgeSearchResponse,
)
def search_knowledge(
    knowledge_base_id: UUID,
    data: KnowledgeSearchRequest,
    membership: OrganizationMember = Depends(
        get_current_membership
    ),
    db: Session = Depends(get_db),
):
    results = retrieve_knowledge(
        db=db,
        organization_id=membership.organization_id,
        knowledge_base_id=knowledge_base_id,
        query=data.query,
        limit=data.limit,
    )

    return {
        "results": results,
        "total": len(results),
    }
