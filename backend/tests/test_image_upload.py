import io

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.main import app


def _make_png_bytes(width: int = 2400, height: int = 1800) -> bytes:
    image = Image.new("RGB", (width, height), color=(120, 80, 40))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
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
    assert payload["image_thumbnail_url"].endswith("_thumb.webp")
    assert payload["image_mime_type"] == "image/webp"
    assert payload["image_width"] <= 1600
    assert payload["image_height"] <= 1600
    assert payload["image_file_size"] > 0


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
