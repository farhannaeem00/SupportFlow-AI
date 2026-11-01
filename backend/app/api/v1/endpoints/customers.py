from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_membership, require_roles
from app.models import OrganizationMember
from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
)
from app.services.customer_service import (
    create_customer,
    list_customers,
    get_customer,
    update_customer,
    deactivate_customer,
)


router = APIRouter(
    prefix="/customers",
    tags=["Customers"],
)


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer_endpoint(
    payload: CustomerCreate,
    membership: OrganizationMember = Depends(
        require_roles("owner", "agent")
    ),
    db: Session = Depends(get_db),
):
    try:
        return create_customer(
            db,
            membership.organization_id,
            payload.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("", response_model=list[CustomerResponse])
def get_customers_endpoint(
    search: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    membership: OrganizationMember = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    return list_customers(
        db,
        membership.organization_id,
        search,
        skip,
        limit,
    )


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer_endpoint(
    customer_id: UUID,
    membership: OrganizationMember = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    customer = get_customer(
        db,
        membership.organization_id,
        customer_id,
    )

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    return customer


@router.patch("/{customer_id}", response_model=CustomerResponse)
def update_customer_endpoint(
    customer_id: UUID,
    payload: CustomerUpdate,
    membership: OrganizationMember = Depends(
        require_roles("owner", "agent")
    ),
    db: Session = Depends(get_db),
):
    customer = get_customer(
        db,
        membership.organization_id,
        customer_id,
    )

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    update_data = payload.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No update fields provided",
        )

    try:
        return update_customer(db, customer, update_data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.delete("/{customer_id}", status_code=status.HTTP_200_OK)
def delete_customer_endpoint(
    customer_id: UUID,
    membership: OrganizationMember = Depends(require_roles("owner")),
    db: Session = Depends(get_db),
):
    customer = get_customer(
        db,
        membership.organization_id,
        customer_id,
    )

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    deactivate_customer(db, customer)

    return {"message": "Customer deactivated successfully"}