"""Add artwork image metadata columns

Revision ID: 004
Revises: 003
Create Date: 2026-05-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("artworks", sa.Column("image_thumbnail_url", sa.String(length=512), nullable=True))
    op.add_column("artworks", sa.Column("image_width", sa.Integer(), nullable=True))
    op.add_column("artworks", sa.Column("image_height", sa.Integer(), nullable=True))
    op.add_column("artworks", sa.Column("image_mime_type", sa.String(length=64), nullable=True))
    op.add_column("artworks", sa.Column("image_file_size", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("artworks", "image_file_size")
    op.drop_column("artworks", "image_mime_type")
    op.drop_column("artworks", "image_height")
    op.drop_column("artworks", "image_width")
    op.drop_column("artworks", "image_thumbnail_url")
