"""Artwork AI enrichment status and cached lookup results."""

from alembic import op
import sqlalchemy as sa

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "artworks",
        sa.Column(
            "enrichment_status",
            sa.String(length=32),
            nullable=False,
            server_default="idle",
        ),
    )
    op.add_column(
        "artworks",
        sa.Column("enrichment_stage", sa.String(length=64), nullable=True),
    )
    op.add_column("artworks", sa.Column("enrichment_error", sa.Text(), nullable=True))
    op.add_column("artworks", sa.Column("enrichment_lookup", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("artworks", "enrichment_lookup")
    op.drop_column("artworks", "enrichment_error")
    op.drop_column("artworks", "enrichment_stage")
    op.drop_column("artworks", "enrichment_status")
