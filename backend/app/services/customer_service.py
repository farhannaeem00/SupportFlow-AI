from uuid import UUID

from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import Customer


def create_customer(db: Session, organization_id: UUID, payload: dict):
    email = payload.get("email")

    if email:
        payload["email"] = email.strip().lower()

    customer = Customer(
        organization_id=organization_id,
        **payload,
    )

    try:
        db.add(customer)
        db.commit()
        db.refresh(customer)
        return customer

    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "A customer with this email already exists in your organization"
        ) from exc

    except Exception:
        db.rollback()
        raise


def list_customers(
    db: Session,
    organization_id: UUID,
    search: str | None = None,
    skip: int = 0,
    limit: int = 20,
):
    query = select(Customer).where(
        Customer.organization_id == organization_id,
        Customer.is_active.is_(True),
    )

    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Customer.full_name.ilike(term),
                Customer.email.ilike(term),
                Customer.phone.ilike(term),
                Customer.company.ilike(term),
            )
        )

    return db.scalars(
        query.order_by(
        Customer.created_at.desc(),
        Customer.id.desc(),
)
        .offset(skip)
        .limit(limit)
    ).all()


def get_customer(
    db: Session,
    organization_id: UUID,
    customer_id: UUID,
):
    return db.scalar(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.organization_id == organization_id,
            Customer.is_active.is_(True),
        )
    )


def update_customer(
    db: Session,
    customer: Customer,
    payload: dict,
):
    if "email" in payload and payload["email"]:
        payload["email"] = payload["email"].strip().lower()

    for field, value in payload.items():
        setattr(customer, field, value)

    try:
        db.commit()
        db.refresh(customer)
        return customer

    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "A customer with this email already exists in your organization"
        ) from exc

    except Exception:
        db.rollback()
        raise



def deactivate_customer(db: Session, customer: Customer):
    customer.is_active = False
    db.commit()
    return True