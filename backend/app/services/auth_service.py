
import re
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Organization, OrganizationMember, User
from app.core.security import hash_password, verify_password


def create_unique_slug(db: Session, name: str) -> str:
    base_slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    base_slug = base_slug[:150] or "workspace"

    slug = base_slug
    counter = 1

    while db.scalar(
        select(Organization.id).where(Organization.slug == slug)
    ):
        counter += 1
        slug = f"{base_slug[:165]}-{counter}"

    return slug


def register_user(
    db: Session,
    full_name: str,
    email: str,
    password: str,
    organization_name: str,
):
    normalized_email = email.strip().lower()

    existing_user = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    if existing_user:
        raise ValueError("An account with this email already exists")

    try:
        user = User(
            full_name=full_name.strip(),
            email=normalized_email,
            hashed_password=hash_password(password),
        )

        db.add(user)
        db.flush()

        organization = Organization(
            name=organization_name.strip(),
            slug=create_unique_slug(db, organization_name),
        )

        db.add(organization)
        db.flush()

        membership = OrganizationMember(
            user_id=user.id,
            organization_id=organization.id,
            role="owner",
        )

        db.add(membership)
        db.commit()

        db.refresh(user)
        db.refresh(organization)

        return user, organization

    except Exception:
        db.rollback()
        raise


def authenticate_user(db: Session, email: str, password: str):
    normalized_email = email.strip().lower()

    user = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    if not user or not user.is_active:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user
