
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization_ai_settings import OrganizationAISettings
from app.schemas.organization_ai_settings import OrganizationAISettingsUpdate


def get_or_create_ai_settings(
    db: Session,
    organization_id: UUID,
) -> OrganizationAISettings:
    settings = db.scalar(
        select(OrganizationAISettings).where(
            OrganizationAISettings.organization_id == organization_id
        )
    )

    if settings is not None:
        return settings

    settings = OrganizationAISettings(
        organization_id=organization_id,
    )

    db.add(settings)
    db.commit()
    db.refresh(settings)

    return settings


def update_ai_settings(
    db: Session,
    organization_id: UUID,
    data: OrganizationAISettingsUpdate,
) -> OrganizationAISettings:
    settings = get_or_create_ai_settings(db, organization_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(settings, field, value)

    db.commit()
    db.refresh(settings)

    return settings
