import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_create_annotation_with_tags_and_links(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit_response = await client.post(
            "/api/visits",
            headers=auth_headers,
            json={
                "museum_name": "National Gallery of Art",
                "city": "Washington, DC",
                "visit_date": "2026-05-25",
            },
        )
        visit_id = visit_response.json()["id"]

        entity_response = await client.post(
            "/api/cultural-entities",
            headers=auth_headers,
            json={
                "visit_id": visit_id,
                "entity_type": "concept",
                "name": "Manifest Destiny",
                "description": None,
                "themes": [],
                "concepts": [],
                "movements": [],
                "historical_events": [],
                "related_entities": [],
            },
        )
        entity_id = entity_response.json()["id"]

        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Western landscape", "visit_id": visit_id},
        )
        artwork_id = artwork_response.json()["id"]

        create_response = await client.post(
            f"/api/artworks/{artwork_id}/annotations",
            headers=auth_headers,
            json={
                "x_percent": 22.0,
                "y_percent": 44.0,
                "category": "history",
                "text": "Expansion myth in the horizon line.",
                "tags": ["colonialism", "migration"],
                "linked_entity_ids": [entity_id],
                "linked_concept_names": ["American identity"],
            },
        )

        assert create_response.status_code == 201
        created = create_response.json()
        assert created["tags"] == ["colonialism", "migration"]
        assert created["linked_entity_ids"] == [entity_id]
        assert created["linked_concept_names"] == ["American identity"]

        list_response = await client.get(f"/api/artworks/{artwork_id}/annotations")
        assert list_response.status_code == 200
        listed = list_response.json()[0]
        assert listed["tags"] == ["colonialism", "migration"]


@pytest.mark.asyncio
async def test_existing_annotations_default_empty_tag_fields(auth_headers: dict[str, str]) -> None:
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
        visit_id = visit_response.json()["id"]

        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Plain annotation", "visit_id": visit_id},
        )
        artwork_id = artwork_response.json()["id"]

        create_response = await client.post(
            f"/api/artworks/{artwork_id}/annotations",
            headers=auth_headers,
            json={
                "x_percent": 10,
                "y_percent": 20,
                "category": "observation",
                "text": "Simple note",
            },
        )
        assert create_response.status_code == 201
        payload = create_response.json()
        assert payload["tags"] == []
        assert payload["linked_entity_ids"] == []
        assert payload["linked_concept_names"] == []


@pytest.mark.asyncio
async def test_update_annotation_tags(auth_headers: dict[str, str]) -> None:
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
        visit_id = visit_response.json()["id"]

        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Update tags", "visit_id": visit_id},
        )
        artwork_id = artwork_response.json()["id"]

        create_response = await client.post(
            f"/api/artworks/{artwork_id}/annotations",
            headers=auth_headers,
            json={
                "x_percent": 30,
                "y_percent": 40,
                "category": "composition",
                "text": "Diagonal movement",
            },
        )
        annotation_id = create_response.json()["id"]

        patch_response = await client.patch(
            f"/api/artworks/{artwork_id}/annotations/{annotation_id}",
            headers=auth_headers,
            json={
                "tags": ["gesture", "composition"],
                "linked_concept_names": ["labor"],
            },
        )

        assert patch_response.status_code == 200
        updated = patch_response.json()
        assert updated["tags"] == ["gesture", "composition"]
        assert updated["linked_concept_names"] == ["labor"]
