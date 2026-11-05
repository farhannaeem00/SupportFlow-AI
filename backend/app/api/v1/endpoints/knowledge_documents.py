
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import (
    get_current_membership,
    require_roles,
)
from app.models import OrganizationMember
from app.schemas.knowledge_document import KnowledgeDocumentResponse
from app.services import knowledge_document_service
from app.services.knowledge.document_processing_service import (
    process_knowledge_document,
)


router = APIRouter(
    prefix="/knowledge-bases/{knowledge_base_id}/documents",
    tags=["Knowledge Documents"],
)


@router.post(
    "",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    background_tasks: BackgroundTasks,
    knowledge_base_id: UUID,
    file: UploadFile = File(...),
    membership: OrganizationMember = Depends(
        require_roles("owner", "admin")
    ),
    db: Session = Depends(get_db),
):
    document = await knowledge_document_service.upload_document(
        db=db,
        organization_id=membership.organization_id,
        knowledge_base_id=knowledge_base_id,
        user_id=membership.user_id,
        file=file,
    )

    background_tasks.add_task(
        process_knowledge_document,
        membership.organization_id,
        knowledge_base_id,
        document.id,
    )

    return document


@router.get(
    "",
    response_model=list[KnowledgeDocumentResponse],
)
def list_documents(
    knowledge_base_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    membership: OrganizationMember = Depends(
        get_current_membership
    ),
    db: Session = Depends(get_db),
):
    return knowledge_document_service.list_documents(
        db,
        membership.organization_id,
        knowledge_base_id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{document_id}",
    response_model=KnowledgeDocumentResponse,
)
def get_document(
    knowledge_base_id: UUID,
    document_id: UUID,
    membership: OrganizationMember = Depends(
        get_current_membership
    ),
    db: Session = Depends(get_db),
):
    return knowledge_document_service.get_document(
        db,
        membership.organization_id,
        knowledge_base_id,
        document_id,
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document(
    knowledge_base_id: UUID,
    document_id: UUID,
    membership: OrganizationMember = Depends(
        require_roles("owner", "admin")
    ),
    db: Session = Depends(get_db),
):
    knowledge_document_service.delete_document(
        db,
        membership.organization_id,
        knowledge_base_id,
        document_id,
    )
