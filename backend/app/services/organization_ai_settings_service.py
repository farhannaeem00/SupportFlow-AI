from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization_ai_settings import OrganizationAISettings
from app.schemas.organization_ai_settings import OrganizationAISettingsUpdate
from app.services.audit_log_service import record_audit_log


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
    actor_id: UUID,
    data: OrganizationAISettingsUpdate,
) -> OrganizationAISettings:
    try:
        settings = db.scalar(
            select(OrganizationAISettings).where(
                OrganizationAISettings.organization_id == organization_id
            )
        )

        if settings is None:
            settings = OrganizationAISettings(
                organization_id=organization_id,
            )
            db.add(settings)
            db.flush()

        changed_fields = []

        for field, value in data.model_dump(exclude_unset=True).items():
            if value is None:
                continue

            if getattr(settings, field) != value:
                setattr(settings, field, value)
                changed_fields.append(field)

        if changed_fields:
            record_audit_log(
                db,
                organization_id=organization_id,
                actor_id=actor_id,
                action="ai_settings_updated",
                resource_type="organization_ai_settings",
                resource_id=organization_id,
                details={
                    "updated_fields": sorted(changed_fields),
                },
            )

        db.commit()
        db.refresh(settings)

        return settings

    except Exception:
        db.rollback()
        raise