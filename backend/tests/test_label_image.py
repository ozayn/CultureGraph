"""Tests for museum label image upload."""

from __future__ import annotations

import io

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.main import app
from app.schemas import ResearchDraft
from app.services.image_upload import process_and_store_label_image, remove_label_image_files
from app.services.lookup_query import build_retrieval_lookup_query


def _make_png_bytes() -> bytes:
    image = Image.new("RGB", (1200, 800), color=(240, 240, 235))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class _ArtworkStub:
    title = None
    artist = None
    year_period = None
    medium = None
    personal_notes = None
    label_ocr_text = "Title: Four Dancers\nArtist: Edgar Degas"


def test_process_and_store_label_image_creates_webp_derivatives(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.services.image_upload.settings.upload_dir", str(tmp_path))

    saved = process_and_store_label_image(
        artwork_id=42,
        data=_make_png_bytes(),
        filename="label.png",
        content_type="image/png",
    )

    assert saved.label_image_url.endswith("_display.webp")
    assert saved.label_image_thumbnail_url.endswith("_thumb.webp")
    remove_label_image_files(
        label_image_url=saved.label_image_url,
        label_image_thumbnail_url=saved.label_image_thumbnail_url,
    )


def test_retrieval_lookup_prioritizes_artwork_label_ocr() -> None:
    draft = ResearchDraft(
        short_summary="Visual analysis",
        historical_context="Context",
        visual_elements_to_notice=[],
        related_questions=[],
        visual_hypothesis_title="Maybe Four Dancers",
        visual_hypothesis_artist="Edgar Degas",
    )
    built = build_retrieval_lookup_query(_ArtworkStub(), None, draft, museum_name=None)  # type: ignore[arg-type]

    assert built.query_source == "ocr_label"
    assert built.query_used == "Four Dancers · Edgar Degas"


@pytest.mark.asyncio
async def test_upload_and_delete_label_image(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Label upload test"},
        )
        artwork_id = artwork_response.json()["id"]

        upload_response = await client.post(
            f"/api/artworks/{artwork_id}/label-image",
            headers=auth_headers,
            files={"file": ("label.png", _make_png_bytes(), "image/png")},
        )

        assert upload_response.status_code == 200
        payload = upload_response.json()
        assert payload["label_image_url"].endswith("_display.webp")
        assert payload["label_image_thumbnail_url"].endswith("_thumb.webp")
        assert payload["label_uploaded_at"] is not None

        delete_response = await client.delete(
            f"/api/artworks/{artwork_id}/label-image",
            headers=auth_headers,
        )

    assert delete_response.status_code == 200
    cleared = delete_response.json()
    assert cleared["label_image_url"] is None
    assert cleared["label_ocr_text"] is None
