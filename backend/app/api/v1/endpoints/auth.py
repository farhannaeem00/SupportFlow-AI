
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

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
from app.services.auth_service import register_user, authenticate_user


router = APIRouter(prefix="/auth", tags=["Authentication"])


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
    db: Session = Depends(get_db),
):
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
    db: Session = Depends(get_db),
):
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
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
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
