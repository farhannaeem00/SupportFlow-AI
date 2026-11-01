from fastapi import APIRouter, Depends

from app.dependencies import get_current_membership
from app.models import OrganizationMember
from app.schemas.organization import OrganizationContextResponse


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