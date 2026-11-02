
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

from sqlalchemy import CheckConstraint

class ConversationAIInsight(Base):
    __tablename__ = "conversation_ai_insights"

    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            name="uq_conversation_ai_insights_conversation_id",
        ),
        Index(
            "ix_conversation_ai_insights_organization_id",
            "organization_id",
        ),
        CheckConstraint(
       "suggestion_status IN ('pending', 'approved', 'rejected')",
       name="ck_conversation_ai_insights_suggestion_status",
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

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )

    intent: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    sentiment: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    requires_human: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    reasoning: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    suggested_reply: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    suggestion_status: Mapped[str] = mapped_column(
    String(20),
    default="pending",
    nullable=False,
)

reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
)

reviewed_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
)
