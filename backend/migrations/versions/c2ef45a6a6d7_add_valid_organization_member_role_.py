"""add valid organization member role constraint

Revision ID: c2ef45a6a6d7
Revises: 551b816049af
Create Date: 2026-11-03 12:10:35.602424

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2ef45a6a6d7'
down_revision: Union[str, None] = '551b816049af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_organization_member_valid_role",
        "organization_members",
        "role IN ('owner', 'agent')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_organization_member_valid_role",
        "organization_members",
        type_="check",
    )