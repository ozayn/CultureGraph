"""Add artwork image region (crop) metadata."""

from alembic import op
import sqlalchemy as sa

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("artworks", sa.Column("image_master_url", sa.String(512), nullable=True))
    op.add_column("artworks", sa.Column("crop_x_percent", sa.Float(), nullable=True))
    op.add_column("artworks", sa.Column("crop_y_percent", sa.Float(), nullable=True))
    op.add_column("artworks", sa.Column("crop_width_percent", sa.Float(), nullable=True))
    op.add_column("artworks", sa.Column("crop_height_percent", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("artworks", "crop_height_percent")
    op.drop_column("artworks", "crop_width_percent")
    op.drop_column("artworks", "crop_y_percent")
    op.drop_column("artworks", "crop_x_percent")
    op.drop_column("artworks", "image_master_url")
