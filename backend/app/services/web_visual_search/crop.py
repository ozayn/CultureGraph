"""Crop helpers for web visual search providers."""

from __future__ import annotations

from app.models import Artwork
from app.services.artwork_image_region import region_from_artwork


def build_normalized_crop_parameter(artwork: Artwork) -> str | None:
    region = region_from_artwork(artwork)
    if region is None or region.is_full_image():
        return None

    left = max(0.0, min(1.0, region.x_percent / 100.0))
    top = max(0.0, min(1.0, region.y_percent / 100.0))
    right = max(0.0, min(1.0, (region.x_percent + region.width_percent) / 100.0))
    bottom = max(0.0, min(1.0, (region.y_percent + region.height_percent) / 100.0))

    if right <= left or bottom <= top:
        return None

    return f"{left:.4f};{top:.4f};{right:.4f};{bottom:.4f}"
