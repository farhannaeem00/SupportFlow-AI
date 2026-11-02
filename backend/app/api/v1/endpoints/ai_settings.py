
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_membership
from app.models.organization_member import OrganizationMember
from app.schemas.organization_ai_settings import (
    OrganizationAISettingsResponse,
    OrganizationAISettingsUpdate,
)
from app.services.organization_ai_settings_service import (
    get_or_create_ai_settings,
    update_ai_settings,
)

router = APIRouter(
    prefix="/ai-settings",
    tags=["AI Settings"],
)


@router.get(
    "",
    response_model=OrganizationAISettingsResponse,
)
def get_ai_settings(
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(get_current_membership),
):
    if membership.role not in {"owner", "agent"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view AI settings.",
        )

    return get_or_create_ai_settings(
        db,
        membership.organization_id,
    )


@router.patch(
    "",
    response_model=OrganizationAISettingsResponse,
)
def patch_ai_settings(
    data: OrganizationAISettingsUpdate,
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(get_current_membership),
):
    if membership.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners can update AI settings.",
        )

    return update_ai_settings(
        db,
        membership.organization_id,
        data,
    )
