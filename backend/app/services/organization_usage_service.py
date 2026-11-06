
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import (
    Conversation,
    KnowledgeBase,
    KnowledgeDocument,
    Organization,
    OrganizationMember,
    OrganizationUsage,
    OrganizationUsageLimit,
)


LIMIT_FIELDS = {
    "team_members": "max_team_members",
    "knowledge_bases": "max_knowledge_bases",
    "documents": "max_documents",
    "storage_bytes": "max_storage_bytes",
    "monthly_conversations": "max_monthly_conversations",
    "monthly_ai_operations": "max_monthly_ai_operations",
}


def current_period_start() -> date:
    now = datetime.now(timezone.utc).date()
    return now.replace(day=1)


def lock_organization(
    db: Session,
    organization_id: UUID,
) -> Organization:
    organization = db.scalar(
        select(Organization)
        .where(Organization.id == organization_id)
        .with_for_update()
    )

    if organization is None:
        raise HTTPException(
            status_code=404,
            detail="Organization not found.",
        )

    return organization


def get_organization_limits(
    db: Session,
    organization_id: UUID,
) -> OrganizationUsageLimit | None:
    return db.get(OrganizationUsageLimit, organization_id)


def _count(
    db: Session,
    model,
    organization_id: UUID,
) -> int:
    return db.scalar(
        select(func.count())
        .select_from(model)
        .where(model.organization_id == organization_id)
    ) or 0


def get_current_usage(
    db: Session,
    organization_id: UUID,
) -> dict:
    period_start = current_period_start()

    storage_bytes = db.scalar(
        select(func.coalesce(func.sum(KnowledgeDocument.file_size), 0))
        .where(KnowledgeDocument.organization_id == organization_id)
    ) or 0

    monthly_usage = db.get(
        OrganizationUsage,
        (organization_id, period_start),
    )

    return {
        "team_members": _count(
            db, OrganizationMember, organization_id
        ),
        "knowledge_bases": _count(
            db, KnowledgeBase, organization_id
        ),
        "documents": _count(
            db, KnowledgeDocument, organization_id
        ),
        "storage_bytes": int(storage_bytes),
        "monthly_conversations": (
            monthly_usage.conversations_created if monthly_usage else 0
        ),
        "monthly_ai_operations": (
            monthly_usage.ai_operations if monthly_usage else 0
        ),
        "monthly_ai_operations_reserved": (
            monthly_usage.ai_operations_reserved if monthly_usage else 0
        ),
        "period_start": period_start,
    }


def get_usage_limits_response(
    db: Session,
    organization_id: UUID,
) -> dict:
    limits = get_organization_limits(db, organization_id)

    return {
        key: getattr(limits, field) if limits else None
        for key, field in LIMIT_FIELDS.items()
    }


def enforce_usage_limit(
    db: Session,
    organization_id: UUID,
    metric: str,
    current_usage: int,
    increment: int = 1,
) -> None:
    limit_field = LIMIT_FIELDS.get(metric)

    if limit_field is None:
        raise ValueError(f"Unsupported usage metric: {metric}")

    limits = get_organization_limits(db, organization_id)
    limit = getattr(limits, limit_field) if limits else None

    if limit is not None and current_usage + increment > limit:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "organization_usage_limit_exceeded",
                "metric": metric,
                "current_usage": current_usage,
                "limit": limit,
                "requested": increment,
            },
        )


def _ensure_monthly_usage(
    db: Session,
    organization_id: UUID,
    period_start: date,
) -> None:
    db.execute(
        insert(OrganizationUsage)
        .values(
            organization_id=organization_id,
            period_start=period_start,
            conversations_created=0,
            ai_operations=0,
            ai_operations_reserved=0,
        )
        .on_conflict_do_nothing(
            index_elements=["organization_id", "period_start"]
        )
    )


def record_conversation_created(
    db: Session,
    organization_id: UUID,
) -> None:
    period_start = current_period_start()

    _ensure_monthly_usage(db, organization_id, period_start)

    db.execute(
        update(OrganizationUsage)
        .where(
            OrganizationUsage.organization_id == organization_id,
            OrganizationUsage.period_start == period_start,
        )
        .values(
            conversations_created=(
                OrganizationUsage.conversations_created + 1
            ),
            updated_at=datetime.now(timezone.utc),
        )
    )


def reserve_ai_operation(
    db: Session,
    organization_id: UUID,
) -> date:
    # Serialize quota checks for this organization. The lock is held
    # only while reserving capacity, never during the external AI call.
    lock_organization(db, organization_id)

    period_start = current_period_start()
    _ensure_monthly_usage(db, organization_id, period_start)

    usage = db.scalar(
        select(OrganizationUsage)
        .where(
            OrganizationUsage.organization_id == organization_id,
            OrganizationUsage.period_start == period_start,
        )
        .with_for_update()
    )

    limits = get_organization_limits(db, organization_id)
    limit = (
        limits.max_monthly_ai_operations
        if limits
        else None
    )

    if (
        limit is not None
        and usage.ai_operations + usage.ai_operations_reserved >= limit
    ):
        db.rollback()
        raise HTTPException(
            status_code=403,
            detail={
                "code": "organization_usage_limit_exceeded",
                "metric": "monthly_ai_operations",
                "current_usage": usage.ai_operations,
                "reserved": usage.ai_operations_reserved,
                "limit": limit,
                "requested": 1,
            },
        )

    usage.ai_operations_reserved += 1
    usage.updated_at = datetime.now(timezone.utc)

    # Persist the reservation before the external AI operation starts.
    db.commit()

    return period_start


def complete_ai_operation(
    db: Session,
    organization_id: UUID,
    period_start: date,
) -> None:
    result = db.execute(
        update(OrganizationUsage)
        .where(
            OrganizationUsage.organization_id == organization_id,
            OrganizationUsage.period_start == period_start,
            OrganizationUsage.ai_operations_reserved > 0,
        )
        .values(
            ai_operations=OrganizationUsage.ai_operations + 1,
            ai_operations_reserved=(
                OrganizationUsage.ai_operations_reserved - 1
            ),
            updated_at=datetime.now(timezone.utc),
        )
    )

    if result.rowcount != 1:
        raise RuntimeError("AI usage reservation could not be completed.")


def release_ai_operation(
    db: Session,
    organization_id: UUID,
    period_start: date,
) -> None:
    db.execute(
        update(OrganizationUsage)
        .where(
            OrganizationUsage.organization_id == organization_id,
            OrganizationUsage.period_start == period_start,
            OrganizationUsage.ai_operations_reserved > 0,
        )
        .values(
            ai_operations_reserved=(
                OrganizationUsage.ai_operations_reserved - 1
            ),
            updated_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
