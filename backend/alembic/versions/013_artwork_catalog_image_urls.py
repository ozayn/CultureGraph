"""Store official catalog image URLs separately from display paths."""

from alembic import op
import sqlalchemy as sa

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("artworks", sa.Column("catalog_image_url", sa.String(length=512), nullable=True))
    op.add_column(
        "artworks", sa.Column("catalog_thumbnail_url", sa.String(length=512), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("artworks", "catalog_thumbnail_url")
    op.drop_column("artworks", "catalog_image_url")
