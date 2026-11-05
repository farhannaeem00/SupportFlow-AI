from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_membership, require_roles
from app.models import OrganizationMember
from app.schemas.team import (
    InviteMemberRequest,
    UpdateMemberRoleRequest,
    TeamMemberResponse,
)
from app.services.team_service import (
    list_team_members,
    add_team_member,
    update_member_role,
    remove_team_member,
)


router = APIRouter(
    prefix="/team",
    tags=["Team Management"],
)


@router.get("/members")
def get_team_members(
    membership: OrganizationMember = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    members = list_team_members(db, membership.organization_id)

    return [
        {
            "id": member.id,
            "full_name": member.user.full_name,
            "email": member.user.email,
            "role": member.role,
            "is_active": member.user.is_active,
        }
        for member in members
    ]


@router.post("/members", status_code=status.HTTP_201_CREATED)
def invite_team_member(
    payload: InviteMemberRequest,
    membership: OrganizationMember = Depends(require_roles("owner")),
    db: Session = Depends(get_db),
):
    try:
        new_member = add_team_member(
            db=db,
            organization_id=membership.organization_id,
            actor_id=membership.user_id,
            full_name=payload.full_name,
            email=payload.email,
            password=payload.password,
            role=payload.role,
        )
        return {
            "message": "Team member created successfully",
            "member_id": str(new_member.id),
        }

    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.patch("/members/{member_id}/role")
def change_member_role(
    member_id: UUID,
    payload: UpdateMemberRoleRequest,
    membership: OrganizationMember = Depends(require_roles("owner")),
    db: Session = Depends(get_db),
):
    try:
        updated = update_member_role(
            db,
            membership.organization_id,
            member_id,
            membership.user_id,
            payload.role,
        )

        if not updated:
            raise HTTPException(status_code=404, detail="Team member not found")

        return {"message": "Member role updated successfully"}

    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.delete("/members/{member_id}")
def delete_team_member(
    member_id: UUID,
    membership: OrganizationMember = Depends(require_roles("owner")),
    db: Session = Depends(get_db),
):
    try:
        result = remove_team_member(
            db,
            membership.organization_id,
            member_id,
            membership.user_id,
        )

        if not result:
            raise HTTPException(status_code=404, detail="Team member not found")

        return {"message": "Team member removed successfully"}

    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))