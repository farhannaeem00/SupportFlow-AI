
"""
add widget rate limits

Revision ID: 551b816049af
Revises: 689f4812cf02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "551b816049af"
down_revision: Union[str, None] = "689f4812cf02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "widget_rate_limits",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "client_key_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "action",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "window_start",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "request_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "client_key_hash",
            "action",
            "window_start",
            name="uq_widget_rate_limit_window",
        ),
    )

    op.create_index(
        "ix_widget_rate_limits_organization_id",
        "widget_rate_limits",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_widget_rate_limits_organization_id",
        table_name="widget_rate_limits",
    )

    op.drop_table("widget_rate_limits")
