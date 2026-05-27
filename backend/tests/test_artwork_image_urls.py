from app.services.artwork_image_urls import (
    is_invalid_image_reference,
    is_upload_path,
    normalize_artwork_image_fields,
    normalize_artwork_image_update,
    upgrade_nga_iiif_display_url,
)


def test_upgrade_nga_thumb_to_display_size() -> None:
    thumb = (
        "https://api.nga.gov/iiif/0fd27212-b70a-4a0b-9e7c-ed0d8bbe7ebf/full/!200,200/0/default.jpg"
    )
    display = upgrade_nga_iiif_display_url(thumb)
    assert display is not None
    assert "!1600,1600" in display
    assert "!200,200" not in display


def test_pick_thumbnail_precedence() -> None:
    normalized = normalize_artwork_image_fields(
        {
            "image_url": "/uploads/artworks/1/display.webp",
            "image_thumbnail_url": "/uploads/artworks/1/thumb.webp",
            "catalog_image_url": "https://example.com/full.jpg",
            "catalog_thumbnail_url": "https://example.com/thumb.jpg",
        }
    )
    assert normalized["image_url"] == "/uploads/artworks/1/display.webp"
    assert normalized["image_thumbnail_url"] == "/uploads/artworks/1/thumb.webp"


def test_legacy_nga_thumb_only_gets_display_url() -> None:
    thumb = (
        "https://api.nga.gov/iiif/0fd27212-b70a-4a0b-9e7c-ed0d8bbe7ebf/full/!200,200/0/default.jpg"
    )
    normalized = normalize_artwork_image_fields(
        {
            "image_url": thumb,
            "image_thumbnail_url": thumb,
            "catalog_image_url": None,
            "catalog_thumbnail_url": None,
        }
    )
    assert normalized["image_url"] is not None
    assert "!1600,1600" in normalized["image_url"]
    assert normalized["image_thumbnail_url"] == thumb


def test_invalid_local_path_is_cleared() -> None:
    normalized = normalize_artwork_image_fields(
        {
            "image_url": "/Users/oz/Dropbox/photo.jpg",
            "image_thumbnail_url": None,
        }
    )
    assert normalized["image_url"] is None


def test_normalize_update_sets_catalog_urls_for_official_image() -> None:
    thumb = "https://ids.si.edu/ids/download?id=SAAM-1_thumb"
    full = "https://ids.si.edu/ids/download?id=SAAM-1_screen"
    data = normalize_artwork_image_update(
        {
            "image_url": full,
            "image_thumbnail_url": thumb,
        }
    )
    assert data["catalog_image_url"] == full
    assert data["catalog_thumbnail_url"] == thumb


def test_upload_path_detection() -> None:
    assert is_upload_path("/uploads/artworks/1/thumb.webp")
    assert is_upload_path("uploads/artworks/1/thumb.webp")
    assert not is_upload_path("https://example.com/x.jpg")
    assert is_invalid_image_reference("/Users/oz/x.jpg")
