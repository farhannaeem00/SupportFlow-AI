from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "b7e2c91a4f60"
down_revision = "de6315e7690c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization_usage_limits",
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("max_team_members", sa.Integer(), nullable=True),
        sa.Column("max_knowledge_bases", sa.Integer(), nullable=True),
        sa.Column("max_documents", sa.Integer(), nullable=True),
        sa.Column("max_storage_bytes", sa.Integer(), nullable=True),
        sa.Column(
            "max_monthly_conversations",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "max_monthly_ai_operations",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
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

    op.create_table(
        "organization_usage",
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("period_start", sa.Date(), primary_key=True),
        sa.Column(
            "conversations_created",
            sa.Integer(),
            nullable=False,
            
        ),
        sa.Column(
            "ai_operations",
            sa.Integer(),
            nullable=False,
            
        ),
        sa.Column(
            "ai_operations_reserved",
            sa.Integer(),
            nullable=False,
            
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            """
            conversations_created >= 0
            AND ai_operations >= 0
            AND ai_operations_reserved >= 0
            """,
            name="ck_organization_usage_counters_non_negative",
        ),
    )


def downgrade() -> None:
    op.drop_table("organization_usage")
    op.drop_table("organization_usage_limits")