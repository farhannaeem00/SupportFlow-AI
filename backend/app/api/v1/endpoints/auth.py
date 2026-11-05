
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import create_access_token
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.auth import (
    AuthOrganizationResponse,
    AuthResponse,
    LoginRequest,
    OrganizationResponse,
    RegisterRequest,
    UserResponse,
)
from app.services.auth_rate_limit_service import enforce_auth_rate_limit
from app.services.auth_service import authenticate_user, register_user

import logging
from urllib.parse import urlencode

from sqlalchemy import select

from app.schemas.auth import (
    PasswordResetRequest,
    PasswordResetConfirmRequest,
)
from app.services.email_service import send_password_reset_email
from app.services.password_reset_service import (
    create_password_reset_token,
    reset_user_password,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

def enforce_auth_limit(
    request: Request,
    db: Session,
    action: str,
    limit: int,
    email: str | None = None,
) -> None:
    client_ip = request.client.host if request.client else "unknown"

    # Independent IP-based limit.
    enforce_auth_rate_limit(
        db=db,
        client_key=f"ip:{client_ip}",
        action=f"{action}_ip" if email else action,
        limit=limit,
    )

    # Independent account-based limit.
    if email:
        enforce_auth_rate_limit(
            db=db,
            client_key=f"email:{email.strip().lower()}",
            action=f"{action}_email",
            limit=limit,
        )


def build_auth_response(user: User) -> AuthResponse:
    organizations = [
        AuthOrganizationResponse(
            id=membership.organization.id,
            name=membership.organization.name,
            slug=membership.organization.slug,
            public_key=membership.organization.public_key,
            role=membership.role,
        )
        for membership in user.memberships
        if membership.organization.is_active
    ]

    organizations.sort(key=lambda organization: organization.name.lower())

    return AuthResponse(
        access_token=create_access_token(user.id),
        user=UserResponse.model_validate(user),
        organization=(
            OrganizationResponse(
                id=organizations[0].id,
                name=organizations[0].name,
                slug=organizations[0].slug,
                public_key=organizations[0].public_key,
            )
            if organizations
            else None
        ),
        organizations=organizations,
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    enforce_auth_limit(
        request=request,
        db=db,
        action="register",
        limit=settings.auth_register_rate_limit,
    )

    try:
        user, _ = register_user(
            db=db,
            full_name=payload.full_name,
            email=str(payload.email),
            password=payload.password,
            organization_name=payload.organization_name,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return build_auth_response(user)


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    enforce_auth_limit(
        request=request,
        db=db,
        action="login",
        limit=settings.auth_login_rate_limit,
        email=str(payload.email),
    )

    user = authenticate_user(
        db,
        str(payload.email),
        payload.password,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return build_auth_response(user)


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.post("/token", tags=["Authentication"])
def oauth2_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    enforce_auth_limit(
        request=request,
        db=db,
        action="token",
        limit=settings.auth_token_rate_limit,
        email=form_data.username,
    )

    user = authenticate_user(
        db,
        email=form_data.username,
        password=form_data.password,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
    }

@router.post("/password-reset/request")
def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    normalized_email = str(payload.email).strip().lower()

    enforce_auth_limit(
        request=request,
        db=db,
        action="password_reset",
        limit=settings.password_reset_rate_limit,
        email=normalized_email,
    )

    user = db.scalar(
        select(User).where(User.email == normalized_email)
    )

    if user and user.is_active:
        raw_token = create_password_reset_token(db, user)

        separator = (
            "&"
            if "?" in settings.password_reset_frontend_url
            else "?"
        )

        reset_url = (
            f"{settings.password_reset_frontend_url}"
            f"{separator}{urlencode({'token': raw_token})}"
        )

        try:
            send_password_reset_email(user.email, reset_url)
        except Exception:
            logger.exception(
                "Password reset email delivery failed for user %s",
                user.id,
            )

            # Local development only. Never log reset links in production.
            if settings.debug:
                logger.warning(
                    "Development password reset URL: %s",
                    reset_url,
                )

    return {
        "message": (
            "If an account exists with that email, "
            "password reset instructions will be sent."
        )
    }


@router.post("/password-reset/confirm")
def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    db: Session = Depends(get_db),
):
    success = reset_user_password(
        db=db,
        token=payload.token,
        new_password=payload.new_password,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token.",
        )

    return {
        "message": "Password reset successfully. You can now sign in."
    }