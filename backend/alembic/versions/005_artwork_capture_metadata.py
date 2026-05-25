"""Add artwork photo capture metadata from EXIF."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("artworks", sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "artworks",
        sa.Column("captured_date_source", sa.String(length=16), nullable=False, server_default="none"),
    )
    op.alter_column("artworks", "captured_date_source", server_default=None)


def downgrade() -> None:
    op.drop_column("artworks", "captured_date_source")
    op.drop_column("artworks", "captured_at")
