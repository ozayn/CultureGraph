"""Crop artwork uploads to a selected region of the full photo."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException
from PIL import Image

from app.services.image_upload import (
    DISPLAY_MAX_EDGE,
    THUMBNAIL_MAX_EDGE,
    THUMB_WEBP_QUALITY,
    WEBP_QUALITY,
    _resize_max_edge,
    _save_webp,
    image_token_from_url,
)


@dataclass(frozen=True)
class ArtworkImageRegion:
    x_percent: float
    y_percent: float
    width_percent: float
    height_percent: float

    def is_full_image(self) -> bool:
        return (
            self.x_percent <= 0.01
            and self.y_percent <= 0.01
            and self.width_percent >= 99.9
            and self.height_percent >= 99.9
        )


@dataclass(frozen=True)
class RegeneratedArtworkImages:
    image_url: str
    image_thumbnail_url: str
    image_width: int
    image_height: int
    image_file_size: int
    crop_x_percent: float | None
    crop_y_percent: float | None
    crop_width_percent: float | None
    crop_height_percent: float | None


def validate_region(region: ArtworkImageRegion) -> ArtworkImageRegion:
    if region.width_percent < 5 or region.height_percent < 5:
        raise HTTPException(status_code=400, detail="Selected area must be at least 5% of the image.")
    if region.x_percent + region.width_percent > 100.01:
        raise HTTPException(status_code=400, detail="Selected area extends beyond the image width.")
    if region.y_percent + region.height_percent > 100.01:
        raise HTTPException(status_code=400, detail="Selected area extends beyond the image height.")
    return region


def crop_image_by_percent(image: Image.Image, region: ArtworkImageRegion) -> Image.Image:
    width, height = image.size
    left = int(round(width * region.x_percent / 100))
    top = int(round(height * region.y_percent / 100))
    right = int(round(width * (region.x_percent + region.width_percent) / 100))
    bottom = int(round(height * (region.y_percent + region.height_percent) / 100))
    right = min(width, max(right, left + 1))
    bottom = min(height, max(bottom, top + 1))
    return image.crop((left, top, right, bottom))


def region_from_artwork(artwork) -> ArtworkImageRegion | None:
    if (
        artwork.crop_x_percent is None
        or artwork.crop_y_percent is None
        or artwork.crop_width_percent is None
        or artwork.crop_height_percent is None
    ):
        return None
    return ArtworkImageRegion(
        x_percent=artwork.crop_x_percent,
        y_percent=artwork.crop_y_percent,
        width_percent=artwork.crop_width_percent,
        height_percent=artwork.crop_height_percent,
    )


def crop_fields_for_region(region: ArtworkImageRegion | None) -> dict[str, float | None]:
    if region is None or region.is_full_image():
        return {
            "crop_x_percent": None,
            "crop_y_percent": None,
            "crop_width_percent": None,
            "crop_height_percent": None,
        }
    return {
        "crop_x_percent": round(region.x_percent, 2),
        "crop_y_percent": round(region.y_percent, 2),
        "crop_width_percent": round(region.width_percent, 2),
        "crop_height_percent": round(region.height_percent, 2),
    }


def regenerate_artwork_derivatives(
    *,
    artwork_id: int,
    image_url: str,
    image_thumbnail_url: str,
    image_master_url: str | None,
    region: ArtworkImageRegion | None,
) -> RegeneratedArtworkImages:
    token = image_token_from_url(image_url)
    if not token:
        raise HTTPException(status_code=400, detail="Artwork image is missing or invalid.")

    from app.config import settings

    upload_root = Path(settings.upload_dir).resolve()
    artwork_dir = upload_root / "artworks" / str(artwork_id)
    master_path = artwork_dir / f"{token}_master.webp"
    if not master_path.is_file() and image_master_url:
        master_relative = image_master_url.removeprefix("/uploads/").lstrip("/")
        master_path = (upload_root / master_relative).resolve()

    if not master_path.is_file():
        display_relative = image_url.removeprefix("/uploads/").lstrip("/")
        display_path = (upload_root / display_relative).resolve()
        if not display_path.is_file():
            raise HTTPException(status_code=400, detail="Original artwork image file not found.")
        master_image = Image.open(display_path)
    else:
        master_image = Image.open(master_path)

    with master_image:
        if master_image.mode != "RGB":
            working = master_image.convert("RGB")
        else:
            working = master_image.copy()

        if region is not None and not region.is_full_image():
            validate_region(region)
            source = crop_image_by_percent(working, region)
        else:
            source = working

        display = _resize_max_edge(source, DISPLAY_MAX_EDGE)
        thumbnail = _resize_max_edge(display, THUMBNAIL_MAX_EDGE)

        display_path = artwork_dir / f"{token}_display.webp"
        thumb_path = artwork_dir / f"{token}_thumb.webp"
        display_size = _save_webp(display, display_path, quality=WEBP_QUALITY)
        _save_webp(thumbnail, thumb_path, quality=THUMB_WEBP_QUALITY)

        crop_fields = crop_fields_for_region(region)
        return RegeneratedArtworkImages(
            image_url=image_url,
            image_thumbnail_url=image_thumbnail_url,
            image_width=display.size[0],
            image_height=display.size[1],
            image_file_size=display_size,
            **crop_fields,
        )
