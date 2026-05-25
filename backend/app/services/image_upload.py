"""Normalize and store uploaded artwork images."""

from __future__ import annotations

import io
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings

ACCEPTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ACCEPTED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MASTER_MAX_EDGE = 2000
DISPLAY_MAX_EDGE = 1600
THUMBNAIL_MAX_EDGE = 400
WEBP_QUALITY = 85
THUMB_WEBP_QUALITY = 80


@dataclass(frozen=True)
class SavedArtworkImages:
    image_url: str
    image_thumbnail_url: str
    image_width: int
    image_height: int
    image_mime_type: str
    image_file_size: int


async def read_upload_with_limit(file: UploadFile, max_bytes: int | None = None) -> bytes:
    limit = max_bytes or settings.upload_max_bytes
    chunks: list[bytes] = []
    total = 0

    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum upload size is {limit // (1024 * 1024)} MB.",
            )
        chunks.append(chunk)

    if total == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    return b"".join(chunks)


def _validate_upload_metadata(filename: str | None, content_type: str | None) -> None:
    if content_type and content_type.lower() not in ACCEPTED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Unsupported image type. Upload JPEG, PNG, or WebP.",
        )

    suffix = Path(filename or "").suffix.lower()
    if suffix and suffix not in ACCEPTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Unsupported image type. Upload JPEG, PNG, or WebP.",
        )


def _prepare_image(data: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=415,
            detail="Could not read image. Upload a valid JPEG, PNG, or WebP file.",
        ) from exc

    if image.format not in {"JPEG", "PNG", "WEBP"}:
        raise HTTPException(
            status_code=415,
            detail="Unsupported image type. Upload JPEG, PNG, or WebP.",
        )

    image = ImageOps.exif_transpose(image)

    if image.mode in {"RGBA", "LA"}:
        background = Image.new("RGBA", image.size, (255, 255, 255, 255))
        background.alpha_composite(image.convert("RGBA"))
        return background.convert("RGB")

    if image.mode != "RGB":
        return image.convert("RGB")

    return image


def _resize_max_edge(image: Image.Image, max_edge: int) -> Image.Image:
    width, height = image.size
    longest = max(width, height)
    if longest <= max_edge:
        return image.copy()

    scale = max_edge / longest
    new_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def _save_webp(image: Image.Image, path: Path, *, quality: int) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    image.save(
        buffer,
        format="WEBP",
        quality=quality,
        method=6,
        optimize=True,
    )
    data = buffer.getvalue()
    path.write_bytes(data)
    return len(data)


def process_and_store_artwork_image(
    *,
    artwork_id: int,
    data: bytes,
    filename: str | None,
    content_type: str | None,
) -> SavedArtworkImages:
    _validate_upload_metadata(filename, content_type)
    source = _prepare_image(data)

    master = _resize_max_edge(source, MASTER_MAX_EDGE)
    display = _resize_max_edge(master, DISPLAY_MAX_EDGE)
    thumbnail = _resize_max_edge(display, THUMBNAIL_MAX_EDGE)

    token = uuid.uuid4().hex
    upload_root = Path(settings.upload_dir)
    artwork_dir = upload_root / "artworks" / str(artwork_id)
    master_path = artwork_dir / f"{token}_master.webp"
    display_path = artwork_dir / f"{token}_display.webp"
    thumb_path = artwork_dir / f"{token}_thumb.webp"

    _save_webp(master, master_path, quality=WEBP_QUALITY)
    display_size = _save_webp(display, display_path, quality=WEBP_QUALITY)
    _save_webp(thumbnail, thumb_path, quality=THUMB_WEBP_QUALITY)

    display_width, display_height = display.size
    return SavedArtworkImages(
        image_url=f"/uploads/artworks/{artwork_id}/{display_path.name}",
        image_thumbnail_url=f"/uploads/artworks/{artwork_id}/{thumb_path.name}",
        image_width=display_width,
        image_height=display_height,
        image_mime_type="image/webp",
        image_file_size=display_size,
    )


def remove_artwork_image_files(
    *,
    image_url: str | None,
    image_thumbnail_url: str | None,
) -> None:
    upload_root = Path(settings.upload_dir).resolve()
    seen_tokens: set[str] = set()

    for url in (image_url, image_thumbnail_url):
        if not url:
            continue
        relative = url.removeprefix("/uploads/").lstrip("/")
        if not relative or relative == url:
            continue
        path = (upload_root / relative).resolve()
        if upload_root not in path.parents and path != upload_root:
            continue
        token = path.name.split("_", 1)[0]
        if not token or token in seen_tokens:
            continue
        seen_tokens.add(token)
        for sibling in path.parent.glob(f"{token}_*"):
            if sibling.is_file():
                sibling.unlink(missing_ok=True)
