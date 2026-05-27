"""Normalize artwork image fields when applying catalog or external URLs."""

from app.services.artwork_image_urls import normalize_artwork_image_update

__all__ = ["normalize_artwork_image_update"]
