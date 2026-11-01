from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import OrganizationMember, User


VALID_ROLES = {"owner", "agent"}


def list_team_members(db: Session, organization_id):
    return db.scalars(
        select(OrganizationMember)
        .join(User)
        .where(OrganizationMember.organization_id == organization_id)
        .order_by(User.created_at.asc())
    ).all()


def add_team_member(
    db: Session,
    organization_id,
    full_name: str,
    email: str,
    password: str,
    role: str,
):
    email = email.strip().lower()
    role = role.strip().lower()

    if role not in VALID_ROLES:
        raise ValueError("Invalid role")

    existing_user = db.scalar(
        select(User).where(User.email == email)
    )

    if existing_user:
        raise ValueError("A user with this email already exists")

    try:
        user = User(
            full_name=full_name.strip(),
            email=email,
            hashed_password=hash_password(password),
        )

        db.add(user)
        db.flush()

        membership = OrganizationMember(
            user_id=user.id,
            organization_id=organization_id,
            role=role,
        )

        db.add(membership)
        db.commit()
        db.refresh(membership)

        return membership

    except Exception:
        db.rollback()
        raise


def update_member_role(
    db: Session,
    organization_id,
    member_id,
    new_role: str,
):
    new_role = new_role.strip().lower()

    if new_role not in VALID_ROLES:
        raise ValueError("Invalid role")

    membership = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == organization_id,
        )
    )

    if not membership:
        return None

    if membership.role == "owner" and new_role != "owner":
        owner_count = db.scalar(
            select(func.count())
            .select_from(OrganizationMember)
            .where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.role == "owner",
            )
        )

        if owner_count <= 1:
            raise ValueError("An organization must have at least one owner")

    membership.role = new_role
    db.commit()
    db.refresh(membership)

    return membership


def remove_team_member(
    db: Session,
    organization_id,
    member_id,
    current_user_id,
):
    membership = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == organization_id,
        )
    )

    if not membership:
        return None

    if membership.user_id == current_user_id:
        raise ValueError("You cannot remove your own membership")

    if membership.role == "owner":
        owner_count = db.scalar(
            select(func.count())
            .select_from(OrganizationMember)
            .where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.role == "owner",
            )
        )

        if owner_count <= 1:
            raise ValueError("An organization must have at least one owner")

    db.delete(membership)
    db.commit()

    return True