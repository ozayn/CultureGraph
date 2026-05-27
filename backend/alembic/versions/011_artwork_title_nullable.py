"""Allow nullable artwork titles for quick photo capture."""

from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "artworks",
        "title",
        existing_type=sa.String(255),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "artworks",
        "title",
        existing_type=sa.String(255),
        nullable=False,
    )
