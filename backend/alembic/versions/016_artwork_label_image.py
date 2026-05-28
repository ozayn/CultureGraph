"""016 — Museum wall label image fields on artworks."""

from alembic import op
import sqlalchemy as sa

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("artworks", sa.Column("label_image_url", sa.String(length=512), nullable=True))
    op.add_column(
        "artworks",
        sa.Column("label_image_thumbnail_url", sa.String(length=512), nullable=True),
    )
    op.add_column("artworks", sa.Column("label_ocr_text", sa.Text(), nullable=True))
    op.add_column(
        "artworks",
        sa.Column("label_uploaded_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("artworks", "label_uploaded_at")
    op.drop_column("artworks", "label_ocr_text")
    op.drop_column("artworks", "label_image_thumbnail_url")
    op.drop_column("artworks", "label_image_url")
