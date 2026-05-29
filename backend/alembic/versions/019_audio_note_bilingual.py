"""Bilingual fields for audio notes."""

from alembic import op
import sqlalchemy as sa

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audio_notes", sa.Column("transcript_original", sa.Text(), nullable=True))
    op.add_column("audio_notes", sa.Column("detected_language", sa.String(length=16), nullable=True))
    op.add_column("audio_notes", sa.Column("transcript_english", sa.Text(), nullable=True))
    op.execute(
        "UPDATE audio_notes SET transcript_original = transcript WHERE transcript IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("audio_notes", "transcript_english")
    op.drop_column("audio_notes", "detected_language")
    op.drop_column("audio_notes", "transcript_original")
