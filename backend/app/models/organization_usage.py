import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OrganizationUsageLimit(Base):
    __tablename__ = "organization_usage_limits"

    __table_args__ = (
        CheckConstraint(
            """
            (max_team_members IS NULL OR max_team_members >= 0)
            AND (max_knowledge_bases IS NULL OR max_knowledge_bases >= 0)
            AND (max_documents IS NULL OR max_documents >= 0)
            AND (max_storage_bytes IS NULL OR max_storage_bytes >= 0)
            AND (
                max_monthly_conversations IS NULL
                OR max_monthly_conversations >= 0
            )
            AND (
                max_monthly_ai_operations IS NULL
                OR max_monthly_ai_operations >= 0
            )
            """,
            name="ck_organization_usage_limits_non_negative",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )

    max_team_members: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    max_knowledge_bases: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    max_documents: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    max_storage_bytes: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    max_monthly_conversations: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    max_monthly_ai_operations: Mapped[int | None] = mapped_column(
        Integer, nullable=True
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


class OrganizationUsage(Base):
    __tablename__ = "organization_usage"

    __table_args__ = (
        CheckConstraint(
            """
            conversations_created >= 0
            AND ai_operations >= 0
            AND ai_operations_reserved >= 0
            """,
            name="ck_organization_usage_counters_non_negative",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )

    period_start: Mapped[date] = mapped_column(
        Date,
        primary_key=True,
    )

    conversations_created: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    ai_operations: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Temporary reservations prevent concurrent requests exceeding the limit.
    ai_operations_reserved: Mapped[int] = mapped_column(
        Integer,
        default=0,
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