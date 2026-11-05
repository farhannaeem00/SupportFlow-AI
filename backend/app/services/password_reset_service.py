import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import hash_password
from app.models import PasswordResetToken, User


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_password_reset_token(
    db: Session,
    user: User,
) -> str:
    now = datetime.now(timezone.utc)

    # Invalidate all previous unused reset tokens.
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )

    raw_token = secrets.token_urlsafe(32)

    reset_token = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_reset_token(raw_token),
        expires_at=now + timedelta(
            minutes=settings.password_reset_token_expire_minutes
        ),
    )

    db.add(reset_token)
    db.commit()

    return raw_token


def reset_user_password(
    db: Session,
    token: str,
    new_password: str,
) -> bool:
    now = datetime.now(timezone.utc)

    reset_token = db.scalar(
        select(PasswordResetToken)
        .where(
            PasswordResetToken.token_hash == hash_reset_token(token)
        )
        .with_for_update()
    )

    if (
        not reset_token
        or reset_token.used_at is not None
        or reset_token.expires_at <= now
    ):
        return False

    user = db.scalar(
        select(User)
        .where(User.id == reset_token.user_id)
        .with_for_update()
    )

    if not user or not user.is_active:
        return False

    user.hashed_password = hash_password(new_password)
    reset_token.used_at = now

    # Invalidate every other outstanding token for this user.
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.id != reset_token.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )

    db.commit()
    return True