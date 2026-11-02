
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OrganizationAISettings(Base):
    __tablename__ = "organization_ai_settings"

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            name="uq_organization_ai_settings_organization_id",
        ),
        CheckConstraint(
            "confidence_threshold >= 0 AND confidence_threshold <= 1",
            name="ck_ai_settings_confidence_threshold",
        ),
        CheckConstraint(
            "escalation_priority_level >= 1 AND escalation_priority_level <= 4",
            name="ck_ai_settings_escalation_priority",
        ),
        CheckConstraint(
            "max_context_messages >= 1 AND max_context_messages <= 50",
            name="ck_ai_settings_max_context_messages",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    ai_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    suggestions_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    confidence_threshold: Mapped[float] = mapped_column(
        Float,
        default=0.60,
        nullable=False,
    )

    # 1=low, 2=normal, 3=high, 4=urgent
    escalation_priority_level: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
    )

    max_context_messages: Mapped[int] = mapped_column(
        Integer,
        default=20,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
