import pytest

from app.services.artwork_images import normalize_artwork_image_update


def test_external_image_url_sets_thumbnail_and_clears_dimensions() -> None:
    data = normalize_artwork_image_update(
        {"image_url": "https://example.com/nga/thumb.jpg"}
    )

    assert data["image_url"] == "https://example.com/nga/thumb.jpg"
    assert data["image_thumbnail_url"] == "https://example.com/nga/thumb.jpg"
    assert data["image_width"] is None
    assert data["image_mime_type"] is None


def test_clearing_image_url_clears_thumbnail_and_dimensions() -> None:
    data = normalize_artwork_image_update({"image_url": None})

    assert data["image_url"] is None
    assert data["image_thumbnail_url"] is None
    assert data["image_file_size"] is None


def test_explicit_thumbnail_is_preserved() -> None:
    data = normalize_artwork_image_update(
        {
            "image_url": "https://example.com/full.jpg",
            "image_thumbnail_url": "https://example.com/thumb.jpg",
        }
    )

    assert data["image_thumbnail_url"] == "https://example.com/thumb.jpg"


def test_local_upload_path_is_not_auto_thumbnailed() -> None:
    data = normalize_artwork_image_update(
        {"image_url": "/uploads/artworks/1/abc_display.webp"}
    )

    assert "image_thumbnail_url" not in data
