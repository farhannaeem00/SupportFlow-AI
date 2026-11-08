
import csv
import io
import json
import re
import zipfile
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select

from app.database import get_db
from app.dependencies import require_roles
from app.models.audit_log import AuditLog
from app.models.conversation import Conversation
from app.models.conversation_ai_insight import ConversationAIInsight
from app.models.conversation_event import ConversationEvent
from app.models.customer import Customer
from app.models.knowledge_base import KnowledgeBase, KnowledgeDocument
from app.models.message import Message
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.user import User
from app.services.organization_usage_service import (
    get_current_usage,
    get_usage_limits_response,
)

CSV_FIELDS = {
    "organization": [
        "id", "name", "slug", "public_key", "is_active",
        "created_at", "updated_at",
    ],
    "usage": [
        "team_members", "knowledge_bases", "documents",
        "storage_bytes", "monthly_conversations",
        "monthly_ai_operations", "period_start",
    ],
    "usage_limits": [
        "team_members", "knowledge_bases", "documents",
        "storage_bytes", "monthly_conversations",
        "monthly_ai_operations",
    ],
    "team_members": [
        "id", "user_id", "full_name", "email", "is_active",
        "role", "joined_at",
    ],
    "customers": [
        "id", "full_name", "email", "phone", "company",
        "is_active", "created_at", "updated_at",
    ],
    "conversations": [
        "id", "customer_id", "assigned_to_id", "subject",
        "status", "priority", "channel", "created_at", "updated_at",
    ],
    "messages": [
        "id", "conversation_id", "sender_type", "sender_user_id",
        "sender_customer_id", "content", "message_type", "created_at",
    ],
    "conversation_events": [
        "id", "conversation_id", "actor_id", "event_type",
        "old_value", "new_value", "created_at",
    ],
    "ai_insights": [
        "id", "conversation_id", "intent", "sentiment", "priority",
        "confidence", "requires_human", "reasoning", "suggested_reply",
        "suggested_reply_sources", "analyzed_at", "suggestion_status",
        "reviewed_by_id", "reviewed_at",
    ],
    "knowledge_bases": [
        "id", "name", "description", "is_active",
        "created_at", "updated_at",
    ],
    "knowledge_documents": [
        "id", "knowledge_base_id", "uploaded_by", "original_filename",
        "content_type", "file_size", "checksum", "status",
        "chunk_count", "created_at", "updated_at",
    ],
    "audit_logs": [
        "id", "actor_id", "action", "resource_type",
        "resource_id", "details", "created_at",
    ],
}
router = APIRouter(prefix="/exports", tags=["Data Exports"])


def _json_value(value):
    """Convert supported Python values into JSON-compatible values."""
    if isinstance(value, (UUID, datetime, date)):
        return value.isoformat() if isinstance(value, (datetime, date)) else str(value)

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]

    return value


def _record(**values):
    return {key: _json_value(value) for key, value in values.items()}


def _model_data(model):
    """Support both Pydantic v2 models and dictionaries."""
    if isinstance(model, dict):
        return dict(model)

    if hasattr(model, "model_dump"):
        return model.model_dump()

    if hasattr(model, "dict"):
        return model.dict()

    return dict(model)


def _build_export(db, organization_id):
    organization = db.scalar(
        select(Organization).where(
            Organization.id == organization_id,
            Organization.is_active.is_(True),
        )
    )

    if organization is None:
        raise HTTPException(
            status_code=404,
            detail="Organization not found",
        )

    # Team members: export only organization memberships and safe user fields.
    memberships = db.execute(
        select(OrganizationMember, User)
        .join(User, User.id == OrganizationMember.user_id)
        .where(OrganizationMember.organization_id == organization_id)
        .order_by(OrganizationMember.joined_at.asc())
    ).all()

    team_members = [
        _record(
            id=membership.id,
            user_id=user.id,
            full_name=user.full_name,
            email=user.email,
            is_active=user.is_active,
            role=membership.role,
            joined_at=membership.joined_at,
        )
        for membership, user in memberships
    ]

    customers = [
        _record(
            id=item.id,
            full_name=item.full_name,
            email=item.email,
            phone=item.phone,
            company=item.company,
            is_active=item.is_active,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in db.scalars(
            select(Customer)
            .where(Customer.organization_id == organization_id)
            .order_by(Customer.created_at.asc(), Customer.id.asc())
        ).all()
    ]

    conversations = [
        _record(
            id=item.id,
            customer_id=item.customer_id,
            assigned_to_id=item.assigned_to_id,
            subject=item.subject,
            status=item.status,
            priority=item.priority,
            channel=item.channel,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in db.scalars(
            select(Conversation)
            .where(Conversation.organization_id == organization_id)
            .order_by(Conversation.created_at.asc(), Conversation.id.asc())
        ).all()
    ]

    # Messages are scoped through their parent conversations.
    messages = [
        _record(
            id=item.id,
            conversation_id=item.conversation_id,
            sender_type=item.sender_type,
            sender_user_id=item.sender_user_id,
            sender_customer_id=item.sender_customer_id,
            content=item.content,
            message_type=item.message_type,
            created_at=item.created_at,
        )
        for item in db.scalars(
            select(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(Conversation.organization_id == organization_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        ).all()
    ]

    # Conversation events are also scoped through their parent conversations.
    conversation_events = [
        _record(
            id=item.id,
            conversation_id=item.conversation_id,
            actor_id=item.actor_id,
            event_type=item.event_type,
            old_value=item.old_value,
            new_value=item.new_value,
            created_at=item.created_at,
        )
        for item in db.scalars(
            select(ConversationEvent)
            .join(
                Conversation,
                Conversation.id == ConversationEvent.conversation_id,
            )
            .where(Conversation.organization_id == organization_id)
            .order_by(
                ConversationEvent.created_at.asc(),
                ConversationEvent.id.asc(),
            )
        ).all()
    ]

    ai_insights = [
        _record(
            id=item.id,
            conversation_id=item.conversation_id,
            intent=item.intent,
            sentiment=item.sentiment,
            priority=item.priority,
            confidence=item.confidence,
            requires_human=item.requires_human,
            reasoning=item.reasoning,
            suggested_reply=item.suggested_reply,
            suggested_reply_sources=item.suggested_reply_sources,
            analyzed_at=item.analyzed_at,
            suggestion_status=item.suggestion_status,
            reviewed_by_id=item.reviewed_by_id,
            reviewed_at=item.reviewed_at,
        )
        for item in db.scalars(
            select(ConversationAIInsight)
            .where(ConversationAIInsight.organization_id == organization_id)
            .order_by(
                ConversationAIInsight.analyzed_at.asc(),
                ConversationAIInsight.id.asc(),
            )
        ).all()
    ]

    knowledge_bases = [
        _record(
            id=item.id,
            name=item.name,
            description=item.description,
            is_active=item.is_active,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in db.scalars(
            select(KnowledgeBase)
            .where(KnowledgeBase.organization_id == organization_id)
            .order_by(KnowledgeBase.created_at.asc(), KnowledgeBase.id.asc())
        ).all()
    ]

    # Export document metadata only. Internal storage filenames and
    # processing error details are intentionally excluded.
    knowledge_documents = [
        _record(
            id=item.id,
            knowledge_base_id=item.knowledge_base_id,
            uploaded_by=item.uploaded_by,
            original_filename=item.original_filename,
            content_type=item.content_type,
            file_size=item.file_size,
            checksum=item.checksum,
            status=item.status,
            chunk_count=item.chunk_count,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item in db.scalars(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.organization_id == organization_id)
            .order_by(
                KnowledgeDocument.created_at.asc(),
                KnowledgeDocument.id.asc(),
            )
        ).all()
    ]

    audit_logs = [
        _record(
            id=item.id,
            actor_id=item.actor_id,
            action=item.action,
            resource_type=item.resource_type,
            resource_id=item.resource_id,
            details=item.details,
            created_at=item.created_at,
        )
        for item in db.scalars(
            select(AuditLog)
            .where(AuditLog.organization_id == organization_id)
            .order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
        ).all()
    ]

    usage = _model_data(get_current_usage(db, organization_id))
    usage.pop("monthly_ai_operations_reserved", None)
    usage.pop("ai_operations_reserved", None)

    limits = _model_data(get_usage_limits_response(db, organization_id))

    datasets = {
        "team_members": team_members,
        "customers": customers,
        "conversations": conversations,
        "messages": messages,
        "conversation_events": conversation_events,
        "ai_insights": ai_insights,
        "knowledge_bases": knowledge_bases,
        "knowledge_documents": knowledge_documents,
        "audit_logs": audit_logs,
    }

    return {
        "export_version": 1,
        "exported_at": datetime.now().astimezone().isoformat(),
        "organization": _record(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            public_key=organization.public_key,
            is_active=organization.is_active,
            created_at=organization.created_at,
            updated_at=organization.updated_at,
        ),
        "usage": _json_value(usage),
        "usage_limits": _json_value(limits),
        "data": datasets,
    }


@router.get("/json")
def export_organization_json(
    membership=Depends(require_roles("owner")),
    db=Depends(get_db),
):
    export_data = _build_export(db, membership.organization_id)

    filename = f"supportflow-{export_data['organization']['slug']}-export.json"

    return Response(
        content=json.dumps(export_data, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


@router.get("/csv")
def export_organization_csv(
    membership=Depends(require_roles("owner")),
    db=Depends(get_db),
):
    export_data = _build_export(db, membership.organization_id)

    memory_file = io.BytesIO()

    with zipfile.ZipFile(
        memory_file,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        # Include organization-level information in its own CSV.
        datasets = {
            "organization": [export_data["organization"]],
            "usage": [export_data["usage"]],
            "usage_limits": [export_data["usage_limits"]],
            **export_data["data"],
        }

        for dataset_name, records in datasets.items():
            csv_buffer = io.StringIO(newline="")

            fieldnames = CSV_FIELDS[dataset_name]

            writer = csv.DictWriter(
                csv_buffer,
                fieldnames=fieldnames,
                extrasaction="ignore",
            )

            if fieldnames:
                writer.writeheader()

                for record in records:
                    writer.writerow({
                        key: (
                            json.dumps(value, ensure_ascii=False)
                            if isinstance(value, (dict, list))
                            else value
                        )
                        for key, value in record.items()
                    })

            archive.writestr(
                f"{dataset_name}.csv",
                csv_buffer.getvalue().encode("utf-8-sig"),
            )

    safe_slug = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "-",
        export_data["organization"]["slug"],
    ).strip("-") or "organization"

    filename = f"supportflow-{safe_slug}-export.zip"

    return Response(
        content=memory_file.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
