"""Normalize artwork image URLs for API responses and updates."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

NGA_IIIF_BASE_RE = re.compile(
    r"^https://api\.nga\.gov/iiif/[0-9a-f-]{36}",
    re.IGNORECASE,
)
NGA_THUMB_SIZE_RE = re.compile(r"/full/!200,200/", re.IGNORECASE)

LOCAL_PATH_MARKERS = ("/Users/", "/home/", "\\", "file://", "C:\\", "D:\\")


def is_public_http_url(value: str | None) -> bool:
    if not value or not value.strip():
        return False
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_upload_path(value: str | None) -> bool:
    if not value or not value.strip():
        return False
    normalized = value.strip().replace("\\", "/")
    return normalized.startswith("/uploads/") or normalized.startswith("uploads/")


def is_invalid_image_reference(value: str | None) -> bool:
    if not value or not value.strip():
        return True
    trimmed = value.strip()
    if is_public_http_url(trimmed) or is_upload_path(trimmed):
        return False
    if trimmed.startswith(LOCAL_PATH_MARKERS):
        return True
    return True


def upgrade_nga_iiif_display_url(url: str | None) -> str | None:
    if not url or not url.strip():
        return None
    trimmed = url.strip()
    if not NGA_IIIF_BASE_RE.match(trimmed):
        return trimmed
    if NGA_THUMB_SIZE_RE.search(trimmed):
        return NGA_THUMB_SIZE_RE.sub("/full/!1600,1600/", trimmed)
    return trimmed


def pick_display_url(data: dict[str, Any]) -> str | None:
    for key in ("image_url", "catalog_image_url", "image_thumbnail_url", "catalog_thumbnail_url"):
        value = data.get(key)
        if is_invalid_image_reference(value):
            continue
        if is_upload_path(value):
            return value.strip()
        if is_public_http_url(value):
            return upgrade_nga_iiif_display_url(value.strip())
    return None


def pick_thumbnail_url(data: dict[str, Any]) -> str | None:
    for key in (
        "image_thumbnail_url",
        "catalog_thumbnail_url",
        "image_url",
        "catalog_image_url",
    ):
        value = data.get(key)
        if is_invalid_image_reference(value):
            continue
        if is_upload_path(value):
            return value.strip()
        if is_public_http_url(value):
            return value.strip()
    return None


def normalize_artwork_image_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with browser-safe image_url / image_thumbnail_url fields."""
    normalized = dict(data)
    display = pick_display_url(normalized)
    thumb = pick_thumbnail_url(normalized)

    if display and is_public_http_url(display):
        normalized["image_url"] = upgrade_nga_iiif_display_url(display)
    elif display and is_upload_path(display):
        path = display if display.startswith("/") else f"/{display.lstrip('/')}"
        normalized["image_url"] = path
    elif is_invalid_image_reference(normalized.get("image_url")):
        normalized["image_url"] = None

    if thumb and is_public_http_url(thumb):
        normalized["image_thumbnail_url"] = thumb
    elif thumb and is_upload_path(thumb):
        path = thumb if thumb.startswith("/") else f"/{thumb.lstrip('/')}"
        normalized["image_thumbnail_url"] = path
    elif is_invalid_image_reference(normalized.get("image_thumbnail_url")):
        normalized["image_thumbnail_url"] = None

    return normalized


def normalize_artwork_image_update(data: dict) -> dict:
    if "image_url" not in data:
        return data

    new_url = data.get("image_url")
    if new_url is None:
        data.setdefault("image_thumbnail_url", None)
        data["image_width"] = None
        data["image_height"] = None
        data["image_mime_type"] = None
        data["image_file_size"] = None
        return data

    if is_invalid_image_reference(new_url):
        raise ValueError("image_url must be an https URL or /uploads path.")

    if is_public_http_url(new_url):
        display = upgrade_nga_iiif_display_url(new_url.strip())
        thumb = data.get("image_thumbnail_url")
        if thumb and is_public_http_url(thumb):
            thumb = thumb.strip()
        else:
            thumb = new_url.strip()
        data["image_url"] = display
        data["image_thumbnail_url"] = thumb
        data.setdefault("catalog_image_url", display)
        data.setdefault("catalog_thumbnail_url", thumb)
        data["image_width"] = None
        data["image_height"] = None
        data["image_mime_type"] = None
        data["image_file_size"] = None
        return data

    if is_upload_path(new_url):
        path = new_url.strip()
        if not path.startswith("/"):
            path = f"/{path.lstrip('/')}"
        data["image_url"] = path
        return data

    raise ValueError("image_url must be an https URL or /uploads path.")
