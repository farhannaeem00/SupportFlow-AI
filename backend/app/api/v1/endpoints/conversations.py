import uuid
from uuid import UUID
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
from app.schemas.conversation import ConversationEventResponse

from app.services.conversation_event_service import (
    get_conversation_events,
)
from app.models.conversation_ai_insight import ConversationAIInsight
from app.schemas.ai import ConversationAIInsightResponse
from app.services.ai.conversation_ai_service import ConversationAIService
from app.dependencies import get_current_membership

from datetime import datetime, timezone

from app.schemas.ai import (
    AISuggestionReviewRequest,
    AISuggestionReviewResponse,
)
from app.models.conversation_ai_insight import ConversationAIInsight

from sqlalchemy import case, select, update

from app.models.conversation import Conversation
from app.models.conversation_ai_insight import ConversationAIInsight
from app.schemas.ai import AIEscalationQueueItem

from sqlalchemy import func

from app.schemas.ai import (
    AIAnalyticsDistribution,
    AIAnalyticsResponse,
)
from typing import Literal


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
    status_filter: Literal[
    "open", "pending", "resolved", "closed"
] | None = Query(default=None, alias="status"),

    priority: Literal[
    "low", "normal", "high", "urgent"
] | None = None, 
    
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

@router.get(
    "/{conversation_id}/events",
    response_model=list[ConversationEventResponse],
)
def get_conversation_activity(
    conversation_id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(get_current_membership),
):
    events = get_conversation_events(
        db=db,
        organization_id=membership.organization_id,
        conversation_id=conversation_id,
        skip=skip,
        limit=limit,
    )

    if events is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    return events


@router.post(
    "/{conversation_id}/ai/analyze",
    response_model=ConversationAIInsightResponse,
)
def analyze_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(get_current_membership),
):
    if membership.role not in {"owner", "agent"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to analyze conversations.",
        )

    service = ConversationAIService()

    try:
        return service.process_conversation(
            db=db,
            organization_id=membership.organization_id,
            conversation_id=conversation_id,
        )
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


@router.get(
    "/{conversation_id}/ai/insights",
    response_model=ConversationAIInsightResponse,
)
def get_conversation_ai_insights(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(get_current_membership),
):
    if membership.role not in {"owner", "agent"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view AI insights.",
        )

    insight = db.scalar(
        select(ConversationAIInsight).where(
            ConversationAIInsight.conversation_id == conversation_id,
            ConversationAIInsight.organization_id == membership.organization_id,
        )
    )

    if insight is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI insights not found for this conversation.",
        )

    return insight


@router.patch(
    "/{conversation_id}/ai/review",
    response_model=AISuggestionReviewResponse,
)
def review_ai_suggestion(
    conversation_id: UUID,
    data: AISuggestionReviewRequest,
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(get_current_membership),
):
    if membership.role not in {"owner", "agent"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to review AI suggestions.",
        )

    insight = db.scalar(
        select(ConversationAIInsight).where(
            ConversationAIInsight.conversation_id == conversation_id,
            ConversationAIInsight.organization_id == membership.organization_id,
        )
    )

    if insight is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI insights not found for this conversation.",
        )

    if not insight.suggested_reply:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="There is no AI-generated suggestion to review.",
        )

    try:
        result = db.execute(
            update(ConversationAIInsight)
            .where(
                ConversationAIInsight.id == insight.id,
                ConversationAIInsight.organization_id == membership.organization_id,
                ConversationAIInsight.suggestion_status == "pending",
                ConversationAIInsight.suggested_reply.is_not(None),
            )
            .values(
                suggestion_status=data.decision,
                reviewed_by_id=membership.user_id,
                reviewed_at=datetime.now(timezone.utc),
            )
            .execution_options(synchronize_session=False)
        )

        if result.rowcount != 1:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This AI suggestion has already been reviewed.",
            )

        db.commit()

        db.refresh(insight)

    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise

    return {
        "conversation_id": insight.conversation_id,
        "suggestion_status": insight.suggestion_status,
        "reviewed_by_id": insight.reviewed_by_id,
        "reviewed_at": insight.reviewed_at,
    }


@router.get(
    "/ai/escalations",
    response_model=list[AIEscalationQueueItem],
)
def get_ai_escalation_queue(
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(get_current_membership),
):
    if membership.role not in {"owner", "agent"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view escalations.",
        )

    priority_order = case(
        (Conversation.priority == "urgent", 1),
        (Conversation.priority == "high", 2),
        (Conversation.priority == "normal", 3),
        else_=4,
    )

    results = db.execute(
        select(Conversation, ConversationAIInsight)
        .join(
            ConversationAIInsight,
            ConversationAIInsight.conversation_id == Conversation.id,
        )
        .where(
            Conversation.organization_id == membership.organization_id,
            ConversationAIInsight.organization_id == membership.organization_id,
            ConversationAIInsight.requires_human.is_(True),
            Conversation.status.notin_(["resolved", "closed"]),
        )
        .order_by(
            priority_order,
            Conversation.created_at.asc(),
        )
        .limit(100)
    ).all()

    return [
        AIEscalationQueueItem(
            conversation_id=conversation.id,
            subject=conversation.subject,
            status=conversation.status,
            priority=conversation.priority,
            assigned_to_id=conversation.assigned_to_id,
            intent=insight.intent,
            sentiment=insight.sentiment,
            confidence=insight.confidence,
            reasoning=insight.reasoning,
            created_at=conversation.created_at,
        )
        for conversation, insight in results
    ]


@router.get(
    "/ai/analytics",
    response_model=AIAnalyticsResponse,
)
def get_ai_analytics(
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(get_current_membership),
):
    if membership.role not in {"owner", "agent"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view AI analytics.",
        )

    organization_id = membership.organization_id

    base_filter = (
        ConversationAIInsight.organization_id == organization_id
    )

    total_analyzed = db.scalar(
        select(func.count(ConversationAIInsight.id)).where(base_filter)
    ) or 0

    escalated_count = db.scalar(
        select(func.count(ConversationAIInsight.id)).where(
            base_filter,
            ConversationAIInsight.requires_human.is_(True),
        )
    ) or 0

    average_confidence = db.scalar(
        select(func.avg(ConversationAIInsight.confidence)).where(base_filter)
    )

    pending_suggestions = db.scalar(
        select(func.count(ConversationAIInsight.id)).where(
            base_filter,
            ConversationAIInsight.suggestion_status == "pending",
        )
    ) or 0

    approved_suggestions = db.scalar(
        select(func.count(ConversationAIInsight.id)).where(
            base_filter,
            ConversationAIInsight.suggestion_status == "approved",
        )
    ) or 0

    rejected_suggestions = db.scalar(
        select(func.count(ConversationAIInsight.id)).where(
            base_filter,
            ConversationAIInsight.suggestion_status == "rejected",
        )
    ) or 0

    intent_rows = db.execute(
        select(
            ConversationAIInsight.intent,
            func.count(ConversationAIInsight.id),
        )
        .where(base_filter)
        .group_by(ConversationAIInsight.intent)
        .order_by(func.count(ConversationAIInsight.id).desc())
    ).all()

    sentiment_rows = db.execute(
        select(
            ConversationAIInsight.sentiment,
            func.count(ConversationAIInsight.id),
        )
        .where(base_filter)
        .group_by(ConversationAIInsight.sentiment)
        .order_by(func.count(ConversationAIInsight.id).desc())
    ).all()

    return AIAnalyticsResponse(
        total_analyzed=total_analyzed,
        escalated_count=escalated_count,
        average_confidence=round(float(average_confidence or 0), 3),
        pending_suggestions=pending_suggestions,
        approved_suggestions=approved_suggestions,
        rejected_suggestions=rejected_suggestions,
        intent_distribution=[
            AIAnalyticsDistribution(name=name, count=count)
            for name, count in intent_rows
        ],
        sentiment_distribution=[
            AIAnalyticsDistribution(name=name, count=count)
            for name, count in sentiment_rows
        ],
    )
