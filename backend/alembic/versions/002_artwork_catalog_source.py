"""Add catalog source metadata to artworks

Revision ID: 002
Revises: 001
Create Date: 2026-05-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("artworks", sa.Column("catalog_source", sa.String(length=128), nullable=True))
    op.add_column("artworks", sa.Column("catalog_object_url", sa.String(length=512), nullable=True))
    op.add_column(
        "artworks", sa.Column("catalog_accession_number", sa.String(length=64), nullable=True)
    )
    op.add_column("artworks", sa.Column("catalog_rights_label", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("artworks", "catalog_rights_label")
    op.drop_column("artworks", "catalog_accession_number")
    op.drop_column("artworks", "catalog_object_url")
    op.drop_column("artworks", "catalog_source")
