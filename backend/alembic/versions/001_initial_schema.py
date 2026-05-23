"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "visits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("museum_name", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=255), nullable=False),
        sa.Column("visit_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "artworks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("visit_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("artist", sa.String(length=255), nullable=True),
        sa.Column("year_period", sa.String(length=100), nullable=True),
        sa.Column("medium", sa.String(length=255), nullable=True),
        sa.Column("museum_gallery", sa.String(length=255), nullable=True),
        sa.Column("image_url", sa.String(length=512), nullable=True),
        sa.Column("personal_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "annotations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("artwork_id", sa.Integer(), nullable=False),
        sa.Column("x_percent", sa.Float(), nullable=False),
        sa.Column("y_percent", sa.Float(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "observation",
                "symbol",
                "history",
                "question",
                "composition",
                name="annotation_category",
            ),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["artwork_id"], ["artworks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "research_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("artwork_id", sa.Integer(), nullable=False),
        sa.Column("short_summary", sa.Text(), nullable=False),
        sa.Column("historical_context", sa.Text(), nullable=False),
        sa.Column("visual_elements_to_notice", sa.Text(), nullable=False),
        sa.Column("related_questions", sa.Text(), nullable=False),
        sa.Column("suggested_annotations", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["artwork_id"], ["artworks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("research_notes")
    op.drop_table("annotations")
    op.drop_table("artworks")
    op.drop_table("visits")
    op.execute("DROP TYPE IF EXISTS annotation_category")
