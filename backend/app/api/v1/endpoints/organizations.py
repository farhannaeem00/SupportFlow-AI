
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_membership
from app.models import (
    OrganizationMember,
    OrganizationUsageLimit,
)
from app.schemas.organization import OrganizationContextResponse
from app.schemas.organization_usage import (
    OrganizationUsageLimits,
    OrganizationUsageLimitsUpdate,
    OrganizationUsageResponse,
)
from app.services.organization_usage_service import (
    get_current_usage,
    get_usage_limits_response,
    lock_organization,
)


router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"],
)


@router.get(
    "/current",
    response_model=OrganizationContextResponse,
)
def get_current_organization(
    membership: OrganizationMember = Depends(get_current_membership),
):
    organization = membership.organization

    return OrganizationContextResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        public_key=organization.public_key,
        role=membership.role,
    )


@router.get(
    "/current/usage",
    response_model=OrganizationUsageResponse,
)
def get_current_organization_usage(
    membership: OrganizationMember = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    organization_id = membership.organization_id

    return {
        "usage": get_current_usage(db, organization_id),
        "limits": get_usage_limits_response(db, organization_id),
    }


@router.patch(
    "/current/usage-limits",
    response_model=OrganizationUsageLimits,
)
def update_organization_usage_limits(
    payload: OrganizationUsageLimitsUpdate,
    membership: OrganizationMember = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    if membership.role != "owner":
        raise HTTPException(
            status_code=403,
            detail="Only organization owners can update usage limits.",
        )

    organization_id = membership.organization_id

    try:
        lock_organization(db, organization_id)

        limits = db.get(OrganizationUsageLimit, organization_id)

        if limits is None:
            limits = OrganizationUsageLimit(
                organization_id=organization_id,
            )
            db.add(limits)

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(limits, field, value)

        limits.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(limits)

        return {
            "team_members": limits.max_team_members,
            "knowledge_bases": limits.max_knowledge_bases,
            "documents": limits.max_documents,
            "storage_bytes": limits.max_storage_bytes,
            "monthly_conversations": limits.max_monthly_conversations,
            "monthly_ai_operations": limits.max_monthly_ai_operations,
        }

    except Exception:
        db.rollback()
        raise
