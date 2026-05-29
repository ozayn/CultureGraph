"""Collection artwork records and image embeddings for visual matching."""

from alembic import op
import sqlalchemy as sa

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collection_artworks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(length=128), nullable=False),
        sa.Column("source_object_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("artist", sa.String(length=512), nullable=True),
        sa.Column("date", sa.String(length=128), nullable=True),
        sa.Column("medium", sa.String(length=512), nullable=True),
        sa.Column("image_url", sa.String(length=1024), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=1024), nullable=True),
        sa.Column("object_url", sa.String(length=1024), nullable=True),
        sa.Column("rights_label", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_name", "source_object_id", name="uq_collection_source_object"),
    )
    op.create_index("ix_collection_artworks_source_name", "collection_artworks", ["source_name"])

    op.create_table(
        "collection_image_embeddings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("collection_artwork_id", sa.Integer(), nullable=False),
        sa.Column("embedding_model", sa.String(length=128), nullable=False),
        sa.Column("embedding_vector", sa.JSON(), nullable=False),
        sa.Column("image_url", sa.String(length=1024), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["collection_artwork_id"],
            ["collection_artworks.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "collection_artwork_id",
            "embedding_model",
            name="uq_collection_embedding_model",
        ),
    )
    op.create_index(
        "ix_collection_image_embeddings_model",
        "collection_image_embeddings",
        ["embedding_model"],
    )


def downgrade() -> None:
    op.drop_index("ix_collection_image_embeddings_model", table_name="collection_image_embeddings")
    op.drop_table("collection_image_embeddings")
    op.drop_index("ix_collection_artworks_source_name", table_name="collection_artworks")
    op.drop_table("collection_artworks")
