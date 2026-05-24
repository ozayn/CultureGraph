from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.routers import import_notes
from app.schemas import MuseumNotesImportRequest
from app.services.museum_notes_import import MockMuseumNotesImportProvider

SAMPLE_NOTES = """
Smithsonian American Art Museum visit notes

Grandma Moses — nighttime baseball scene, small-town lights
Thomas Moran and Manifest Destiny — dramatic western landscape
Sam Gilliam — draped canvas, color fields spilling off the wall
"""


@pytest.mark.asyncio
async def test_mock_import_extracts_structured_draft() -> None:
    provider = MockMuseumNotesImportProvider()
    request = MuseumNotesImportRequest(
        text=SAMPLE_NOTES,
        default_museum="Smithsonian American Art Museum",
        default_city="Washington, DC",
        visit_date=date(2026, 5, 23),
    )

    result = await provider.extract(request)

    assert result.source == "mock"
    assert result.visit.museum_name == "Smithsonian American Art Museum"
    assert result.visit.city == "Washington, DC"
    assert result.visit.visit_date == "2026-05-23"
    assert len(result.artworks) >= 3

    artists = {artwork.artist for artwork in result.artworks if artwork.artist}
    assert "Grandma Moses" in artists
    assert "Thomas Moran" in artists
    assert "Sam Gilliam" in artists

    moran = next(item for item in result.artworks if item.artist == "Thomas Moran")
    assert "Manifest Destiny" in moran.concepts
    assert any(link.target == "Manifest Destiny" for link in result.concept_links)


@pytest.mark.asyncio
async def test_import_endpoint_returns_structured_draft(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        import_notes,
        "get_museum_notes_import_provider",
        lambda: MockMuseumNotesImportProvider(),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/import/museum-notes",
            json={
                "text": SAMPLE_NOTES,
                "default_museum": "Smithsonian American Art Museum",
                "default_city": "Washington, DC",
                "visit_date": "2026-05-23",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "mock"
    assert payload["visit"]["museum_name"] == "Smithsonian American Art Museum"
    assert len(payload["artworks"]) >= 3
    assert payload["artworks"][0]["suggested_annotations"]
