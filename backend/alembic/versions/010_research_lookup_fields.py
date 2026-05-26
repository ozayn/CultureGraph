"""Add possible title/artist fields to research notes for image lookup."""

from alembic import op
import sqlalchemy as sa

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("research_notes", sa.Column("possible_title", sa.String(255), nullable=True))
    op.add_column("research_notes", sa.Column("possible_artist", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("research_notes", "possible_artist")
    op.drop_column("research_notes", "possible_title")
