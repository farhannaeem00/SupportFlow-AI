
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Request,
    status,
)
from app.services.notification_service import (
    notify_new_widget_conversation,
    notify_customer_message,
)
from app.services.webhook_delivery_service import (
    process_due_webhook_deliveries,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Organization, WidgetSession
from app.schemas.widget import (
    WidgetConfigResponse,
    WidgetSessionResponse,
    WidgetConversationCreate,
    WidgetConversationResponse,
    WidgetMessageCreate,
    WidgetMessageResponse,
)
from app.services.widget_service import (
    get_active_organization,
    create_widget_session,
    get_valid_widget_session,
    start_widget_conversation,
    send_widget_message,
    get_widget_conversation,
    get_widget_messages,
)

import logging

from app.services.ai.conversation_ai_service import ConversationAIService

from app.config import settings
from app.services.widget_rate_limit_service import enforce_widget_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/widget",
    tags=["Website Widget"],
)

def process_widget_ai(
    db: Session,
    organization_id: UUID,
    conversation_id: UUID,
) -> None:
    """
    Best-effort AI processing.

    Customer messages are already saved before this function runs.
    An AI provider failure must never cause message submission to fail.
    """
    try:
        service = ConversationAIService()

        insight = service.process_conversation(
            db=db,
            organization_id=organization_id,
            conversation_id=conversation_id,
        )

        if insight.requires_human:
            logger.info(
                "Conversation %s requires human attention.",
                conversation_id,
            )

    except Exception:
        db.rollback()
        logger.exception(
            "AI processing failed for widget conversation %s.",
            conversation_id,
        )


def get_widget_organization(
    public_key: str,
    db: Session,
) -> Organization:
    organization = get_active_organization(db, public_key)

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget not found or inactive.",
        )

    return organization


def get_widget_session(
    organization_id: UUID,
    session_token: str,
    db: Session,
) -> WidgetSession:
    widget_session = get_valid_widget_session(
        db,
        organization_id,
        session_token,
    )

    if widget_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired widget session.",
        )

    return widget_session


@router.get(
    "/{public_key}",
    response_model=WidgetConfigResponse,
)
def get_widget_config(
    public_key: str,
    db: Session = Depends(get_db),
):
    organization = get_widget_organization(public_key, db)

    return WidgetConfigResponse(
        organization_name=organization.name,
    )


@router.post(
    "/{public_key}/sessions",
    response_model=WidgetSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    public_key: str,
    request: Request,
    db: Session = Depends(get_db),
):
    organization = get_widget_organization(public_key, db)

    client_ip = request.client.host if request.client else "unknown"

    enforce_widget_rate_limit(
        db=db,
        organization_id=organization.id,
        client_key=f"ip:{client_ip}",
        action="session",
        limit=settings.widget_session_rate_limit,
    )

    widget_session, raw_token = create_widget_session(
        db,
        organization,
    )

    return WidgetSessionResponse(
        session_token=raw_token,
        expires_at=widget_session.expires_at,
    )


@router.post(
    "/{public_key}/conversations",
    response_model=WidgetConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    public_key: str,
    payload: WidgetConversationCreate,
    background_tasks: BackgroundTasks,
    x_widget_session: str = Header(alias="X-Widget-Session"),
    db: Session = Depends(get_db),
):
    organization = get_widget_organization(public_key, db)

    widget_session = get_widget_session(
        organization.id,
        x_widget_session,
        db,
    )
    enforce_widget_rate_limit(
        db=db,
        organization_id=organization.id,
        client_key=f"session:{x_widget_session}",
        action="conversation",
        limit=settings.widget_conversation_rate_limit,
    )

    if widget_session.conversation_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This visitor session already has a conversation.",
        )

    conversation = start_widget_conversation(
        db=db,
        organization=organization,
        widget_session=widget_session,
        full_name=payload.full_name,
        email=payload.email,
        subject=payload.subject,
        message_content=payload.message,
    )
    background_tasks.add_task(
        process_due_webhook_deliveries,
        limit=20,
    )
    background_tasks.add_task(
        notify_new_widget_conversation,
        organization.id,
        conversation.id,
)

    messages = get_widget_messages(
        db=db,
        organization_id=organization.id,
        conversation_id=conversation.id,
)

    process_widget_ai(
    db=db,
    organization_id=organization.id,
    conversation_id=conversation.id,
)

    return {
        "id": conversation.id,
        "subject": conversation.subject,
        "status": conversation.status,
        "created_at": conversation.created_at,
        "messages": messages,
    }


@router.post(
    "/{public_key}/messages",
    response_model=WidgetMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    public_key: str,
    payload: WidgetMessageCreate,
    background_tasks: BackgroundTasks,
    x_widget_session: str = Header(alias="X-Widget-Session"),
    db: Session = Depends(get_db),
):
    organization = get_widget_organization(public_key, db)

    widget_session = get_widget_session(
        organization.id,
        x_widget_session,
        db,
    )

    # Enforce rate limit BEFORE saving or processing the message.
    enforce_widget_rate_limit(
        db=db,
        organization_id=organization.id,
        client_key=f"session:{x_widget_session}",
        action="message",
        limit=settings.widget_message_rate_limit,
    )

    try:
        message = send_widget_message(
            db,
            widget_session,
            payload.message,
        )
        background_tasks.add_task(
            process_due_webhook_deliveries,
            limit=20,
        )
        if widget_session.conversation_id is not None:
            background_tasks.add_task(
                notify_customer_message,
                organization.id,
                widget_session.conversation_id,
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    # Process AI only after the message has been successfully saved.
    if widget_session.conversation_id is not None:
        process_widget_ai(
            db=db,
            organization_id=organization.id,
            conversation_id=widget_session.conversation_id,
        )

    return message

@router.get(
    "/{public_key}/conversation",
    response_model=WidgetConversationResponse,
)
def get_conversation_history(
    public_key: str,
    x_widget_session: str = Header(alias="X-Widget-Session"),
    db: Session = Depends(get_db),
):
    organization = get_widget_organization(public_key, db)

    widget_session = get_widget_session(
        organization.id,
        x_widget_session,
        db,
    )

    try:
        conversation = get_widget_conversation(
            db,
            widget_session,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    messages = get_widget_messages(
        db=db,
        organization_id=organization.id,
        conversation_id=conversation.id,
)

    return {
        "id": conversation.id,
        "subject": conversation.subject,
        "status": conversation.status,
        "created_at": conversation.created_at,
        "messages": messages,
    }
