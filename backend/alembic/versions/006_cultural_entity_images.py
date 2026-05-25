"""cultural entity image fields

Revision ID: 006
Revises: 005
Create Date: 2026-05-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cultural_entities", sa.Column("image_url", sa.String(length=512), nullable=True))
    op.add_column(
        "cultural_entities", sa.Column("thumbnail_url", sa.String(length=512), nullable=True)
    )
    op.add_column(
        "cultural_entities", sa.Column("image_source_name", sa.String(length=128), nullable=True)
    )
    op.add_column(
        "cultural_entities", sa.Column("image_source_url", sa.String(length=512), nullable=True)
    )
    op.add_column(
        "cultural_entities", sa.Column("image_rights_label", sa.String(length=255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("cultural_entities", "image_rights_label")
    op.drop_column("cultural_entities", "image_source_url")
    op.drop_column("cultural_entities", "image_source_name")
    op.drop_column("cultural_entities", "thumbnail_url")
    op.drop_column("cultural_entities", "image_url")
