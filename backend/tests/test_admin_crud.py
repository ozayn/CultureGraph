"""Tests for admin edit/delete endpoints and auth requirements."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app


async def _create_visit(client: AsyncClient, headers: dict[str, str]) -> int:
    response = await client.post(
        "/api/visits",
        headers=headers,
        json={
            "museum_name": "National Gallery of Art",
            "city": "Washington, DC",
            "visit_date": "2026-05-25",
            "notes": "Admin CRUD visit",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _create_artwork(
    client: AsyncClient, headers: dict[str, str], visit_id: int
) -> int:
    response = await client.post(
        "/api/artworks",
        headers=headers,
        json={"title": "Test artwork", "artist": "Test artist", "visit_id": visit_id},
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.asyncio
async def test_public_cannot_patch_or_delete_visit(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit_id = await _create_visit(client, auth_headers)

        patch_response = await client.patch(
            f"/api/visits/{visit_id}",
            json={"notes": "Public edit attempt"},
        )
        delete_response = await client.delete(f"/api/visits/{visit_id}")

    assert patch_response.status_code == 401
    assert delete_response.status_code == 401


@pytest.mark.asyncio
async def test_admin_can_patch_and_delete_visit(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit_id = await _create_visit(client, auth_headers)
        artwork_id = await _create_artwork(client, auth_headers, visit_id)

        entity_response = await client.post(
            "/api/cultural-entities",
            headers=auth_headers,
            json={
                "visit_id": visit_id,
                "entity_type": "concept",
                "name": "Light and shadow",
                "description": "A recurring theme",
                "themes": ["chiaroscuro"],
                "concepts": [],
                "movements": [],
                "historical_events": [],
                "related_entities": [],
            },
        )
        assert entity_response.status_code == 201
        entity_id = entity_response.json()["id"]

        annotation_response = await client.post(
            f"/api/artworks/{artwork_id}/annotations",
            headers=auth_headers,
            json={
                "x_percent": 10,
                "y_percent": 20,
                "category": "observation",
                "text": "Nested delete test",
            },
        )
        assert annotation_response.status_code == 201
        annotation_id = annotation_response.json()["id"]

        patch_response = await client.patch(
            f"/api/visits/{visit_id}",
            headers=auth_headers,
            json={"notes": "Updated visit notes"},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["notes"] == "Updated visit notes"

        delete_response = await client.delete(f"/api/visits/{visit_id}", headers=auth_headers)
        assert delete_response.status_code == 204

        assert (await client.get(f"/api/visits/{visit_id}")).status_code == 404
        assert (await client.get(f"/api/artworks/{artwork_id}")).status_code == 404
        assert (await client.get(f"/api/cultural-entities/{entity_id}")).status_code == 404
        assert (
            await client.get(f"/api/artworks/{artwork_id}/annotations")
        ).status_code == 404


@pytest.mark.asyncio
async def test_public_cannot_patch_or_delete_artwork(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit_id = await _create_visit(client, auth_headers)
        artwork_id = await _create_artwork(client, auth_headers, visit_id)

        patch_response = await client.patch(
            f"/api/artworks/{artwork_id}",
            json={"title": "Unauthorized edit"},
        )
        delete_response = await client.delete(f"/api/artworks/{artwork_id}")

    assert patch_response.status_code == 401
    assert delete_response.status_code == 401


@pytest.mark.asyncio
async def test_admin_can_patch_and_delete_artwork(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit_id = await _create_visit(client, auth_headers)
        artwork_id = await _create_artwork(client, auth_headers, visit_id)

        patch_response = await client.patch(
            f"/api/artworks/{artwork_id}",
            headers=auth_headers,
            json={"title": "Updated title", "personal_notes": "Updated note"},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["title"] == "Updated title"

        delete_response = await client.delete(
            f"/api/artworks/{artwork_id}", headers=auth_headers
        )
        assert delete_response.status_code == 204
        assert (await client.get(f"/api/artworks/{artwork_id}")).status_code == 404


@pytest.mark.asyncio
async def test_nested_annotation_patch_and_delete(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit_id = await _create_visit(client, auth_headers)
        artwork_id = await _create_artwork(client, auth_headers, visit_id)

        create_response = await client.post(
            f"/api/artworks/{artwork_id}/annotations",
            headers=auth_headers,
            json={
                "x_percent": 33,
                "y_percent": 44,
                "category": "symbol",
                "text": "Original text",
            },
        )
        assert create_response.status_code == 201
        annotation_id = create_response.json()["id"]

        public_patch = await client.patch(
            f"/api/artworks/{artwork_id}/annotations/{annotation_id}",
            json={"text": "Public edit"},
        )
        assert public_patch.status_code == 401

        patch_response = await client.patch(
            f"/api/artworks/{artwork_id}/annotations/{annotation_id}",
            headers=auth_headers,
            json={"text": "Updated text", "category": "history"},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["text"] == "Updated text"
        assert patch_response.json()["category"] == "history"

        delete_response = await client.delete(
            f"/api/artworks/{artwork_id}/annotations/{annotation_id}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 204
        assert (
            await client.get(f"/api/artworks/{artwork_id}/annotations")
        ).json() == []


@pytest.mark.asyncio
async def test_cultural_entity_patch_and_delete(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit_id = await _create_visit(client, auth_headers)

        create_response = await client.post(
            "/api/cultural-entities",
            headers=auth_headers,
            json={
                "visit_id": visit_id,
                "entity_type": "artist",
                "name": "Caravaggio",
                "description": "Baroque painter",
                "themes": [],
                "concepts": [],
                "movements": ["Baroque"],
                "historical_events": [],
                "related_entities": [],
            },
        )
        assert create_response.status_code == 201
        entity_id = create_response.json()["id"]

        public_delete = await client.delete(f"/api/cultural-entities/{entity_id}")
        assert public_delete.status_code == 401

        patch_response = await client.patch(
            f"/api/cultural-entities/{entity_id}",
            headers=auth_headers,
            json={
                "name": "Michelangelo Merisi da Caravaggio",
                "thumbnail_url": "https://example.com/caravaggio-thumb.jpg",
                "image_source_name": "Wikimedia Commons",
                "image_source_url": "https://commons.wikimedia.org/wiki/File:Example.jpg",
                "image_rights_label": "Public domain",
            },
        )
        assert patch_response.status_code == 200
        payload = patch_response.json()
        assert payload["name"] == "Michelangelo Merisi da Caravaggio"
        assert payload["thumbnail_url"] == "https://example.com/caravaggio-thumb.jpg"
        assert payload["image_source_name"] == "Wikimedia Commons"

        delete_response = await client.delete(
            f"/api/cultural-entities/{entity_id}", headers=auth_headers
        )
        assert delete_response.status_code == 204
        assert (await client.get(f"/api/cultural-entities/{entity_id}")).status_code == 404


@pytest.mark.asyncio
async def test_research_note_delete_requires_admin(
    auth_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit_id = await _create_visit(client, auth_headers)
        artwork_id = await _create_artwork(client, auth_headers, visit_id)

        generate_response = await client.post(
            f"/api/artworks/{artwork_id}/research",
            headers=auth_headers,
        )
        assert generate_response.status_code == 200

        notes_response = await client.get(f"/api/artworks/{artwork_id}/research")
        assert notes_response.status_code == 200
        notes = notes_response.json()
        assert len(notes) == 1
        note_id = notes[0]["id"]

        public_delete = await client.delete(
            f"/api/artworks/{artwork_id}/research/{note_id}"
        )
        assert public_delete.status_code == 401

        delete_response = await client.delete(
            f"/api/artworks/{artwork_id}/research/{note_id}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 204
        assert (await client.get(f"/api/artworks/{artwork_id}/research")).json() == []
