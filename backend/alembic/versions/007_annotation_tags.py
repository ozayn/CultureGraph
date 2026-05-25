"""annotation tags and linked entities

Revision ID: 007
Revises: 006
Create Date: 2026-05-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("annotations", sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column(
        "annotations",
        sa.Column("linked_entity_ids", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "annotations",
        sa.Column("linked_concept_names", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("annotations", "linked_concept_names")
    op.drop_column("annotations", "linked_entity_ids")
    op.drop_column("annotations", "tags")
