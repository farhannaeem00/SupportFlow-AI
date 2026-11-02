
"""add AI suggestion knowledge sources

Revision ID: 689f4812cf02
Revises: 8521165862f9
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "689f4812cf02"
down_revision: Union[str, None] = "8521165862f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversation_ai_insights",
        sa.Column("suggested_reply_sources", sa.JSON(), nullable=True),
    )

    op.add_column(
        "conversation_ai_insights",
        sa.Column("reviewed_by_id", sa.UUID(), nullable=True),
    )

    op.add_column(
        "conversation_ai_insights",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_foreign_key(
        "fk_conversation_ai_insights_reviewed_by_id_users",
        "conversation_ai_insights",
        "users",
        ["reviewed_by_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_conversation_ai_insights_reviewed_by_id_users",
        "conversation_ai_insights",
        type_="foreignkey",
    )

    op.drop_column(
        "conversation_ai_insights",
        "reviewed_at",
    )

    op.drop_column(
        "conversation_ai_insights",
        "reviewed_by_id",
    )

    op.drop_column(
        "conversation_ai_insights",
        "suggested_reply_sources",
    )
