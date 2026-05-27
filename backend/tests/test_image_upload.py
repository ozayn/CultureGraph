import io

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.main import app
from app.services.image_upload import extract_capture_datetime, resolve_capture_datetime


def _make_png_bytes(width: int = 2400, height: int = 1800) -> bytes:
    image = Image.new("RGB", (width, height), color=(120, 80, 40))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _make_jpeg_with_exif(*, exif_date: str) -> bytes:
    image = Image.new("RGB", (800, 600), color=(90, 120, 150))
    exif = image.getexif()
    exif[36867] = exif_date
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif.tobytes())
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_upload_normalizes_artwork_image(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit_response = await client.post(
            "/api/visits",
            headers=auth_headers,
            json={
                "museum_name": "Test Museum",
                "city": "Washington, DC",
                "visit_date": "2026-05-25",
            },
        )
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={
                "title": "Upload test",
                "visit_id": visit_response.json()["id"],
            },
        )
        artwork_id = artwork_response.json()["id"]

        upload_response = await client.post(
            f"/api/artworks/{artwork_id}/image",
            headers=auth_headers,
            files={"file": ("photo.png", _make_png_bytes(), "image/png")},
        )

    assert upload_response.status_code == 200
    payload = upload_response.json()
    assert payload["image_url"].endswith("_display.webp")
    assert payload["image_master_url"].endswith("_master.webp")
    assert payload["image_thumbnail_url"].endswith("_thumb.webp")
    assert payload["image_mime_type"] == "image/webp"
    assert payload["image_width"] <= 1600
    assert payload["image_height"] <= 1600
    assert payload["image_file_size"] > 0
    assert payload["captured_at"] is None
    assert payload["captured_date_source"] == "none"


@pytest.mark.asyncio
async def test_upload_extracts_exif_datetime_original(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "EXIF upload"},
        )
        artwork_id = artwork_response.json()["id"]

        upload_response = await client.post(
            f"/api/artworks/{artwork_id}/image",
            headers=auth_headers,
            files={
                "file": (
                    "photo.jpg",
                    _make_jpeg_with_exif(exif_date="2026:05:23 14:30:00"),
                    "image/jpeg",
                )
            },
        )

    assert upload_response.status_code == 200
    payload = upload_response.json()
    assert payload["captured_date_source"] == "exif"
    assert payload["captured_at"] is not None
    assert payload["captured_at"][:10] == "2026-05-23"


def test_extract_capture_datetime_reads_exif_original() -> None:
    captured_at, source = extract_capture_datetime(
        _make_jpeg_with_exif(exif_date="2026:05:23 14:30:00")
    )
    assert source == "exif"
    assert captured_at is not None
    assert captured_at.year == 2026
    assert captured_at.month == 5
    assert captured_at.day == 23
    assert captured_at.hour == 14
    assert captured_at.minute == 30


def test_extract_capture_datetime_without_exif() -> None:
    captured_at, source = extract_capture_datetime(_make_png_bytes())
    assert captured_at is None
    assert source == "none"


def test_extract_capture_datetime_ignores_invalid_exif_date() -> None:
    captured_at, source = extract_capture_datetime(
        _make_jpeg_with_exif(exif_date="not-a-real-date")
    )
    assert captured_at is None
    assert source == "none"


def test_resolve_capture_datetime_uses_client_fallback_without_exif() -> None:
    captured_at, source = resolve_capture_datetime(
        _make_png_bytes(),
        client_captured_at="2026-05-23T14:30:00Z",
    )
    assert source == "exif"
    assert captured_at is not None
    assert captured_at.year == 2026
    assert captured_at.month == 5
    assert captured_at.day == 23


def test_resolve_capture_datetime_prefers_uploaded_exif() -> None:
    jpeg = _make_jpeg_with_exif(exif_date="2026:05:24 10:00:00")
    captured_at, source = resolve_capture_datetime(
        jpeg,
        client_captured_at="2026-05-23T14:30:00Z",
    )
    assert source == "exif"
    assert captured_at is not None
    assert captured_at.day == 24


@pytest.mark.asyncio
async def test_upload_uses_client_captured_at_when_exif_stripped(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Client EXIF fallback"},
        )
        artwork_id = artwork_response.json()["id"]

        upload_response = await client.post(
            f"/api/artworks/{artwork_id}/image",
            headers=auth_headers,
            data={"captured_at": "2026-05-23T14:30:00Z"},
            files={"file": ("photo.png", _make_png_bytes(), "image/png")},
        )

    assert upload_response.status_code == 200
    payload = upload_response.json()
    assert payload["captured_date_source"] == "exif"
    assert payload["captured_at"] is not None
    assert payload["captured_at"][:10] == "2026-05-23"


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_type(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Bad upload"},
        )
        artwork_id = artwork_response.json()["id"]

        upload_response = await client.post(
            f"/api/artworks/{artwork_id}/image",
            headers=auth_headers,
            files={"file": ("notes.txt", b"not an image", "text/plain")},
        )

    assert upload_response.status_code == 415


@pytest.mark.asyncio
async def test_upload_rejects_oversized_file(
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "upload_max_bytes", 1024)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Large upload"},
        )
        artwork_id = artwork_response.json()["id"]

        upload_response = await client.post(
            f"/api/artworks/{artwork_id}/image",
            headers=auth_headers,
            files={"file": ("large.png", _make_png_bytes(), "image/png")},
        )

    assert upload_response.status_code == 413


@pytest.mark.asyncio
async def test_uploaded_image_is_served_from_uploads_route(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Static file test"},
        )
        artwork_id = artwork_response.json()["id"]

        upload_response = await client.post(
            f"/api/artworks/{artwork_id}/image",
            headers=auth_headers,
            files={"file": ("photo.png", _make_png_bytes(400, 300), "image/png")},
        )
        assert upload_response.status_code == 200
        thumb_url = upload_response.json()["image_thumbnail_url"]

        static_response = await client.get(thumb_url)

    assert static_response.status_code == 200
    assert static_response.headers["content-type"].startswith("image/")
    assert static_response.headers.get("cache-control", "").startswith("public")
    assert len(static_response.content) > 0
