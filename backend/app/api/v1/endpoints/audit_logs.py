from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_membership
from app.models import AuditLog, OrganizationMember
from app.schemas.audit_log import AuditLogResponse


router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
)


@router.get(
    "",
    response_model=list[AuditLogResponse],
)
def list_audit_logs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    action: str | None = Query(default=None, max_length=100),
    resource_type: str | None = Query(default=None, max_length=50),
    resource_id: UUID | None = None,
    membership: OrganizationMember = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    if membership.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners can view audit logs.",
        )

    statement = select(AuditLog).where(
        AuditLog.organization_id == membership.organization_id,
    )

    if action:
        statement = statement.where(AuditLog.action == action)

    if resource_type:
        statement = statement.where(
            AuditLog.resource_type == resource_type
        )

    if resource_id:
        statement = statement.where(
            AuditLog.resource_id == resource_id
        )

    statement = (
        statement
        .order_by(
            AuditLog.created_at.desc(),
            AuditLog.id.desc(),
        )
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(statement).all())