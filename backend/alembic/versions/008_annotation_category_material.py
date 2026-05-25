"""Add material annotation category

Revision ID: 008
Revises: 007
Create Date: 2026-05-23

"""

from typing import Sequence, Union

from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE annotation_category ADD VALUE IF NOT EXISTS 'material'")


def downgrade() -> None:
    pass
