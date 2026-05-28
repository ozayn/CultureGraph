"""Shared cleanup helpers for deleting visits and artworks."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Artwork, Visit
from app.services.image_upload import remove_artwork_image_files, remove_label_image_files


def cleanup_artwork_image_files(artwork: Artwork) -> None:
    remove_artwork_image_files(
        image_url=artwork.image_url,
        image_thumbnail_url=artwork.image_thumbnail_url,
    )
    remove_label_image_files(
        label_image_url=artwork.label_image_url,
        label_image_thumbnail_url=artwork.label_image_thumbnail_url,
    )


def delete_artwork(db: Session, artwork: Artwork) -> None:
    cleanup_artwork_image_files(artwork)
    db.delete(artwork)


def delete_visit(db: Session, visit: Visit) -> None:
    for artwork in list(visit.artworks):
        delete_artwork(db, artwork)
    db.delete(visit)
