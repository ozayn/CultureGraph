"""Add cultural_entities table for imported non-artwork entries

Revision ID: 003
Revises: 002
Create Date: 2026-05-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

cultural_entity_type = postgresql.ENUM(
    "artwork",
    "artist",
    "concept",
    "movement",
    "technique",
    "material",
    "historical_event",
    "symbol",
    "architecture",
    "museum_space",
    "political_idea",
    name="cultural_entity_type",
    create_type=False,
)


def upgrade() -> None:
    cultural_entity_type.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "cultural_entities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("visit_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", cultural_entity_type, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("themes", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("concepts", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("movements", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("historical_events", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("related_entities", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["visit_id"], ["visits.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cultural_entities_visit_id", "cultural_entities", ["visit_id"])


def downgrade() -> None:
    op.drop_index("ix_cultural_entities_visit_id", table_name="cultural_entities")
    op.drop_table("cultural_entities")
    cultural_entity_type.drop(op.get_bind(), checkfirst=True)
