"""Audio notes with transcript and AI interpretation."""

from alembic import op
import sqlalchemy as sa

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audio_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("visit_id", sa.Integer(), nullable=True),
        sa.Column("artwork_id", sa.Integer(), nullable=True),
        sa.Column("audio_url", sa.String(length=512), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("cleaned_note", sa.Text(), nullable=True),
        sa.Column("interpretation_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["artwork_id"], ["artworks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audio_notes_visit_id", "audio_notes", ["visit_id"])
    op.create_index("ix_audio_notes_artwork_id", "audio_notes", ["artwork_id"])


def downgrade() -> None:
    op.drop_index("ix_audio_notes_artwork_id", table_name="audio_notes")
    op.drop_index("ix_audio_notes_visit_id", table_name="audio_notes")
    op.drop_table("audio_notes")
