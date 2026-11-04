
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from jose import JWTError, jwt

from app.config import settings


password_hasher = PasswordHasher()

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return password_hasher.verify(hashed_password, password)
    except (VerificationError, InvalidHashError):
        return False


def create_access_token(user_id: UUID) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )

    payload = {
        "sub": str(user_id),
        "exp": expires_at,
        "jti": secrets.token_urlsafe(16),
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[ALGORITHM],
        )

        if not isinstance(payload, dict):
            raise ValueError("Invalid token payload")

        if not isinstance(payload.get("sub"), str) or not payload["sub"].strip():
            raise ValueError("Missing or invalid subject claim")

        if not isinstance(payload.get("jti"), str) or not payload["jti"].strip():
            raise ValueError("Missing or invalid token identifier")

        if "exp" not in payload:
            raise ValueError("Missing expiration claim")

        return payload

    except (JWTError, TypeError, ValueError) as exc:
        raise ValueError("Invalid or expired access token") from exc
