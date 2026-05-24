from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.routers import import_notes
from app.schemas import CulturalEntityType, MuseumNotesImportRequest
from app.services.museum_notes_import import MockMuseumNotesImportProvider

SAMPLE_NOTES = """
Smithsonian American Art Museum visit notes

Grandma Moses — nighttime baseball scene, small-town lights
Thomas Moran and Manifest Destiny — dramatic western landscape
Sam Gilliam — draped canvas, color fields spilling off the wall
WPA mural program in the rotunda
Gesso ground on unprimed canvas
"""


@pytest.mark.asyncio
async def test_mock_import_extracts_multiple_entity_types() -> None:
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
    assert len(result.entities) >= 4

    entity_types = {entity.entity_type for entity in result.entities}
    assert CulturalEntityType.artist in entity_types
    assert CulturalEntityType.artwork in entity_types or CulturalEntityType.artist in entity_types
    assert CulturalEntityType.concept in entity_types or CulturalEntityType.political_idea in entity_types
    assert CulturalEntityType.historical_event in entity_types
    assert (
        CulturalEntityType.material in entity_types
        or CulturalEntityType.technique in entity_types
    )

    moran = next(
        (entity for entity in result.entities if entity.name == "Thomas Moran"),
        None,
    )
    assert moran is not None
    assert moran.entity_type == CulturalEntityType.artist

    manifest = next(
        (entity for entity in result.entities if "Manifest Destiny" in entity.name),
        None,
    )
    assert manifest is not None
    assert manifest.entity_type in {
        CulturalEntityType.political_idea,
        CulturalEntityType.concept,
    }


@pytest.mark.asyncio
async def test_import_endpoint_returns_entity_draft(
    monkeypatch: pytest.MonkeyPatch,
    auth_headers: dict[str, str],
) -> None:
    monkeypatch.setattr(
        import_notes,
        "get_museum_notes_import_provider",
        lambda: MockMuseumNotesImportProvider(),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/import/museum-notes",
            headers=auth_headers,
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
    assert len(payload["entities"]) >= 4
    assert payload["entities"][0]["entity_type"]
