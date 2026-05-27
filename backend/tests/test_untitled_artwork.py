"""Untitled artwork create, upload, research, and metadata apply."""

import io

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from app.main import app


def _make_png_bytes() -> bytes:
    image = Image.new("RGB", (400, 300), color=(100, 100, 100))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_create_artwork_without_title(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"visit_id": None},
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["title"] is None

        get_response = await client.get(f"/api/artworks/{payload['id']}")
        assert get_response.status_code == 200
        assert get_response.json()["title"] is None


@pytest.mark.asyncio
async def test_create_and_upload_image_without_title(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={},
        )
        artwork_id = create_response.json()["id"]

        upload_response = await client.post(
            f"/api/artworks/{artwork_id}/image",
            headers=auth_headers,
            files={"file": ("photo.png", _make_png_bytes(), "image/png")},
        )

    assert upload_response.status_code == 200
    assert upload_response.json()["title"] is None
    assert upload_response.json()["image_url"]


@pytest.mark.asyncio
async def test_research_untitled_artwork(auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.research import MockLLMProvider

    monkeypatch.setattr(
        "app.routers.research.get_research_provider",
        lambda: MockLLMProvider(),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"personal_notes": "Three figures in pastel tones"},
        )
        artwork_id = artwork_response.json()["id"]

        research_response = await client.post(
            f"/api/artworks/{artwork_id}/research",
            headers=auth_headers,
        )

    assert research_response.status_code == 200
    assert research_response.json()["suggested_annotations"]


@pytest.mark.asyncio
async def test_apply_ai_title_to_untitled_artwork(auth_headers: dict[str, str]) -> None:
    from app.database import SessionLocal
    from app.models import ResearchNote

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={},
        )
        artwork_id = artwork_response.json()["id"]

        db = SessionLocal()
        try:
            db.add(
                ResearchNote(
                    artwork_id=artwork_id,
                    short_summary="Four Dancers — possibly by Edgar Degas",
                    historical_context="Context",
                    visual_elements_to_notice="[]",
                    related_questions="[]",
                    suggested_annotations="[]",
                    possible_title="Four Dancers",
                    possible_artist="Edgar Degas",
                )
            )
            db.commit()
        finally:
            db.close()

        update_response = await client.put(
            f"/api/artworks/{artwork_id}",
            headers=auth_headers,
            json={"title": "Four Dancers", "artist": "Edgar Degas"},
        )

    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Four Dancers"


@pytest.mark.asyncio
async def test_empty_title_string_stored_as_null(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "   "},
        )

    assert response.status_code == 201
    assert response.json()["title"] is None
