"""Resolve artwork image URLs for web visual search."""

from __future__ import annotations

from app.config import settings
from app.models import Artwork
from app.services.web_visual_search.crop import build_normalized_crop_parameter
from app.services.web_visual_search.types import LensSearchError, LensSearchQuery


def resolve_public_image_url(image_url: str) -> str:
    normalized = image_url.strip()
    if normalized.startswith("http://") or normalized.startswith("https://"):
        return normalized

    if normalized.startswith("/uploads/"):
        base = (settings.public_api_base_url or "").strip().rstrip("/")
        if not base:
            raise LensSearchError(
                "Web visual search needs a publicly reachable image URL. "
                "Set PUBLIC_API_BASE_URL to your deployed API origin "
                "(for example https://your-api.up.railway.app), "
                "or apply a catalog image URL to the artwork first."
            )
        return f"{base}{normalized}"

    raise LensSearchError("Unsupported artwork image URL for web visual search.")


def resolve_lens_image_url(artwork: Artwork) -> str:
    image_url = (artwork.image_url or "").strip()
    if not image_url:
        raise LensSearchError("Upload a photo before running web visual search.")
    return resolve_public_image_url(image_url)


def build_lens_search_query(artwork: Artwork, *, use_crop: bool) -> LensSearchQuery:
    crop = build_normalized_crop_parameter(artwork) if use_crop else None
    if crop and (artwork.image_master_url or "").strip():
        image_url = resolve_public_image_url(artwork.image_master_url)
        return LensSearchQuery(image_url=image_url, crop=crop)
    return LensSearchQuery(image_url=resolve_lens_image_url(artwork), crop=None)
