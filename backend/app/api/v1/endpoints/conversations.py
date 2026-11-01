import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_membership
from app.models.organization_member import OrganizationMember
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
)
from app.services.conversation_service import (
    create_conversation,
    list_conversations,
)
from app.schemas.conversation import (
    ConversationDetailResponse,
    MessageResponse,
)
from app.services.conversation_service import (
    get_conversation,
    get_conversation_messages,
)
from app.schemas.conversation import MessageCreate
from app.services.message_service import create_agent_message

from app.schemas.conversation import (
    ConversationAssignmentUpdate,
    ConversationStatusUpdate,
    ConversationPriorityUpdate,
)

from app.services.conversation_management_service import (
    assign_conversation,
    update_conversation_status,
    update_conversation_priority,
)


router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation_endpoint(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(get_current_membership),
):
    try:
        return create_conversation(
            db=db,
            organization_id=membership.organization_id,
            payload=payload,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=list[ConversationResponse],
)
def get_conversations(
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = None,
    assigned_to_id: uuid.UUID | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(get_current_membership),
):
    return list_conversations(
        db=db,
        organization_id=membership.organization_id,
        status=status_filter,
        priority=priority,
        assigned_to_id=assigned_to_id,
        skip=skip,
        limit=limit,
    )

@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
)
def get_conversation_details(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(get_current_membership),
):
    conversation = get_conversation(
        db=db,
        organization_id=membership.organization_id,
        conversation_id=conversation_id,
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    return conversation


@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessageResponse],
)
def get_conversation_message_history(
    conversation_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(get_current_membership),
):
    messages = get_conversation_messages(
        db=db,
        organization_id=membership.organization_id,
        conversation_id=conversation_id,
        skip=skip,
        limit=limit,
    )

    if messages is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    return messages

@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def send_agent_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(get_current_membership),
):
    content = payload.content.strip()

    if not content:
        raise HTTPException(
            status_code=422,
            detail="Message content cannot be empty.",
        )

    try:
        return create_agent_message(
            db=db,
            organization_id=membership.organization_id,
            conversation_id=conversation_id,
            agent_id=membership.user_id,
            content=content,
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )


@router.patch(
    "/{conversation_id}/assignment",
    response_model=ConversationResponse,
)
def update_conversation_assignment(
    conversation_id: uuid.UUID,
    payload: ConversationAssignmentUpdate,
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(get_current_membership),
):
    try:
        return assign_conversation(
            db=db,
            organization_id=membership.organization_id,
            conversation_id=conversation_id,
            actor_id=membership.user_id,
            assigned_to_id=payload.assigned_to_id,
        )

    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.patch(
    "/{conversation_id}/status",
    response_model=ConversationResponse,
)
def update_status(
    conversation_id: uuid.UUID,
    payload: ConversationStatusUpdate,
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(get_current_membership),
):
    try:
        return update_conversation_status(
            db=db,
            organization_id=membership.organization_id,
            conversation_id=conversation_id,
            actor_id=membership.user_id,
            new_status=payload.status,
        )

    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.patch(
    "/{conversation_id}/priority",
    response_model=ConversationResponse,
)
def update_priority(
    conversation_id: uuid.UUID,
    payload: ConversationPriorityUpdate,
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(get_current_membership),
):
    try:
        return update_conversation_priority(
            db=db,
            organization_id=membership.organization_id,
            conversation_id=conversation_id,
            actor_id=membership.user_id,
            new_priority=payload.priority,
        )

    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))