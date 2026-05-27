"""015 — Persist visual analysis fields on research notes."""

from alembic import op
import sqlalchemy as sa

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "research_notes",
        sa.Column("period_or_movement", sa.String(length=255), nullable=True),
    )
    op.add_column("research_notes", sa.Column("ocr_label_text", sa.Text(), nullable=True))
    op.add_column("research_notes", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column("research_notes", sa.Column("visual_analysis", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("research_notes", "visual_analysis")
    op.drop_column("research_notes", "confidence")
    op.drop_column("research_notes", "ocr_label_text")
    op.drop_column("research_notes", "period_or_movement")
