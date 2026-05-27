"""Artwork image region selection and derivative regeneration."""

import io

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.main import app
from app.services.artwork_image_region import (
    ArtworkImageRegion,
    crop_image_by_percent,
)


def _make_two_tone_png() -> bytes:
    image = Image.new("RGB", (1000, 800), color=(200, 40, 40))
    for x in range(500, 1000):
        for y in range(400, 800):
            image.putpixel((x, y), (40, 90, 200))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_crop_image_by_percent_extracts_subregion() -> None:
    image = Image.new("RGB", (1000, 800), color=(10, 10, 10))
    for x in range(600, 1000):
        for y in range(300, 800):
            image.putpixel((x, y), (250, 250, 250))

    cropped = crop_image_by_percent(
        image,
        ArtworkImageRegion(x_percent=60, y_percent=37.5, width_percent=40, height_percent=62.5),
    )
    assert cropped.size[0] == 400
    assert cropped.size[1] == 500
    assert cropped.getpixel((0, 0)) == (250, 250, 250)


@pytest.mark.asyncio
async def test_upload_then_set_region_persists(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Region test"},
        )
        artwork_id = artwork_response.json()["id"]

        upload_response = await client.post(
            f"/api/artworks/{artwork_id}/image",
            headers=auth_headers,
            files={"file": ("photo.png", _make_two_tone_png(), "image/png")},
        )
        assert upload_response.status_code == 200
        uploaded = upload_response.json()
        assert uploaded["image_master_url"]
        full_width = uploaded["image_width"]
        full_height = uploaded["image_height"]

        region_response = await client.patch(
            f"/api/artworks/{artwork_id}/image-region",
            headers=auth_headers,
            json={
                "x_percent": 50,
                "y_percent": 50,
                "width_percent": 50,
                "height_percent": 50,
            },
        )
        assert region_response.status_code == 200
        cropped = region_response.json()
        assert cropped["crop_width_percent"] == 50
        assert cropped["image_width"] <= full_width
        assert cropped["image_height"] <= full_height

        get_response = await client.get(f"/api/artworks/{artwork_id}")
        assert get_response.json()["crop_x_percent"] == 50

        reset_response = await client.patch(
            f"/api/artworks/{artwork_id}/image-region",
            headers=auth_headers,
            json={"use_full_image": True},
        )
        assert reset_response.status_code == 200
        reset = reset_response.json()
        assert reset["crop_x_percent"] is None
        assert reset["image_width"] == full_width
        assert reset["image_height"] == full_height
