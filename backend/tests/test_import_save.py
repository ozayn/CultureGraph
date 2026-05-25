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
WPA mural program in the rotunda
Gesso ground on unprimed canvas
"""


@pytest.mark.asyncio
async def test_import_save_creates_visit_and_multiple_entries(
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
        import_response = await client.post(
            "/api/import/museum-notes",
            headers=auth_headers,
            json={
                "text": SAMPLE_NOTES,
                "default_museum": "Smithsonian American Art Museum",
                "default_city": "Washington, DC",
                "visit_date": "2026-05-23",
            },
        )
        assert import_response.status_code == 200
        draft = import_response.json()
        entities = draft["entities"]
        assert len(entities) >= 4

        visit_response = await client.post(
            "/api/visits",
            headers=auth_headers,
            json={
                "museum_name": draft["visit"]["museum_name"],
                "city": draft["visit"]["city"],
                "visit_date": draft["visit"]["visit_date"],
                "notes": draft["visit"]["summary"],
            },
        )
        assert visit_response.status_code == 201
        visit_id = visit_response.json()["id"]

        artwork_entities = [entity for entity in entities if entity["entity_type"] == "artwork"]
        cultural_entities = [
            entity for entity in entities if entity["entity_type"] != "artwork"
        ]

        for entity in artwork_entities:
            artwork_response = await client.post(
                "/api/artworks",
                headers=auth_headers,
                json={
                    "title": entity.get("title") or entity["name"],
                    "artist": entity.get("artist"),
                    "year_period": entity.get("period_or_year"),
                    "medium": entity.get("medium"),
                    "personal_notes": entity.get("description"),
                    "visit_id": visit_id,
                },
            )
            assert artwork_response.status_code == 201

        for entity in cultural_entities:
            cultural_response = await client.post(
                "/api/cultural-entities",
                headers=auth_headers,
                json={
                    "visit_id": visit_id,
                    "entity_type": entity["entity_type"],
                    "name": entity["name"],
                    "description": entity.get("description"),
                    "themes": entity.get("themes") or [],
                    "concepts": entity.get("concepts") or [],
                    "movements": entity.get("movements") or [],
                    "historical_events": entity.get("historical_events") or [],
                    "related_entities": entity.get("related_entities") or [],
                },
            )
            assert cultural_response.status_code == 201

        saved_artworks = await client.get(f"/api/artworks?visit_id={visit_id}")
        saved_cultural = await client.get(f"/api/cultural-entities?visit_id={visit_id}")

    assert saved_artworks.status_code == 200
    assert saved_cultural.status_code == 200
    assert len(saved_artworks.json()) == len(artwork_entities)
    assert len(saved_cultural.json()) == len(cultural_entities)
    assert len(saved_artworks.json()) + len(saved_cultural.json()) >= 4

    saved_names = {artwork["title"] for artwork in saved_artworks.json()} | {
        entity["name"] for entity in saved_cultural.json()
    }
    assert "Thomas Moran" in saved_names or any(
        "Moran" in name for name in saved_names
    )
    assert any("WPA" in name for name in saved_names)
