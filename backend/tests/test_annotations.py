import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_create_and_list_annotations(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit_response = await client.post(
            "/api/visits",
            headers=auth_headers,
            json={
                "museum_name": "National Gallery of Art",
                "city": "Washington, DC",
                "visit_date": "2026-05-25",
                "notes": "Annotation test visit",
            },
        )
        assert visit_response.status_code == 201
        visit_id = visit_response.json()["id"]

        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={
                "title": "Test artwork",
                "artist": "Test artist",
                "visit_id": visit_id,
            },
        )
        assert artwork_response.status_code == 201
        artwork_id = artwork_response.json()["id"]

        empty_list = await client.get(f"/api/artworks/{artwork_id}/annotations")
        assert empty_list.status_code == 200
        assert empty_list.json() == []

        create_response = await client.post(
            f"/api/artworks/{artwork_id}/annotations",
            headers=auth_headers,
            json={
                "x_percent": 42.5,
                "y_percent": 61.25,
                "category": "observation",
                "text": "Notice the brushwork in the upper left.",
            },
        )
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["artwork_id"] == artwork_id
        assert created["x_percent"] == 42.5
        assert created["y_percent"] == 61.25
        assert created["category"] == "observation"
        assert created["text"] == "Notice the brushwork in the upper left."
        assert created["id"] > 0

        list_response = await client.get(f"/api/artworks/{artwork_id}/annotations")
        assert list_response.status_code == 200
        annotations = list_response.json()
        assert len(annotations) == 1
        assert annotations[0]["id"] == created["id"]


@pytest.mark.asyncio
async def test_create_annotation_requires_auth() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/artworks/1/annotations",
            json={
                "x_percent": 10,
                "y_percent": 20,
                "category": "observation",
                "text": "Unauthorized pin",
            },
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_annotation_rejects_invalid_coordinates(
    auth_headers: dict[str, str],
) -> None:
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
            json={"title": "Coordinate test", "visit_id": visit_response.json()["id"]},
        )
        artwork_id = artwork_response.json()["id"]

        response = await client.post(
            f"/api/artworks/{artwork_id}/annotations",
            headers=auth_headers,
            json={
                "x_percent": 120,
                "y_percent": 10,
                "category": "observation",
                "text": "Out of bounds",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_annotation_returns_404_for_missing_artwork(
    auth_headers: dict[str, str],
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/artworks/999999/annotations",
            headers=auth_headers,
            json={
                "x_percent": 50,
                "y_percent": 50,
                "category": "history",
                "text": "Missing artwork",
            },
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_unplaced_annotation(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit_response = await client.post(
            "/api/visits",
            headers=auth_headers,
            json={
                "museum_name": "Unplaced Annotation Museum",
                "city": "Washington, DC",
                "visit_date": "2026-05-25",
            },
        )
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Unplaced artwork", "visit_id": visit_response.json()["id"]},
        )
        artwork_id = artwork_response.json()["id"]

        create_response = await client.post(
            f"/api/artworks/{artwork_id}/annotations",
            headers=auth_headers,
            json={
                "x_percent": None,
                "y_percent": None,
                "category": "observation",
                "text": "Text-only AI suggestion accepted without a pin.",
            },
        )

        assert create_response.status_code == 201
        created = create_response.json()
        assert created["x_percent"] is None
        assert created["y_percent"] is None

        place_response = await client.patch(
            f"/api/artworks/{artwork_id}/annotations/{created['id']}",
            headers=auth_headers,
            json={"x_percent": 24.5, "y_percent": 66.0},
        )

        assert place_response.status_code == 200
        placed = place_response.json()
        assert placed["x_percent"] == 24.5
        assert placed["y_percent"] == 66.0


@pytest.mark.asyncio
async def test_create_annotation_rejects_partial_coordinates(
    auth_headers: dict[str, str],
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit_response = await client.post(
            "/api/visits",
            headers=auth_headers,
            json={
                "museum_name": "Partial Coordinate Museum",
                "city": "Washington, DC",
                "visit_date": "2026-05-25",
            },
        )
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Partial coordinate artwork", "visit_id": visit_response.json()["id"]},
        )
        artwork_id = artwork_response.json()["id"]

        response = await client.post(
            f"/api/artworks/{artwork_id}/annotations",
            headers=auth_headers,
            json={
                "x_percent": 10,
                "y_percent": None,
                "category": "observation",
                "text": "Only one coordinate",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_annotation_text_category_and_tags(
    auth_headers: dict[str, str],
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit_response = await client.post(
            "/api/visits",
            headers=auth_headers,
            json={
                "museum_name": "Edit Museum",
                "city": "Washington, DC",
                "visit_date": "2026-05-25",
            },
        )
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Editable artwork", "visit_id": visit_response.json()["id"]},
        )
        artwork_id = artwork_response.json()["id"]

        create_response = await client.post(
            f"/api/artworks/{artwork_id}/annotations",
            headers=auth_headers,
            json={
                "x_percent": 30.0,
                "y_percent": 40.0,
                "category": "observation",
                "text": "Original note",
                "tags": ["original"],
                "linked_concept_names": ["labor"],
            },
        )
        annotation_id = create_response.json()["id"]

        patch_response = await client.patch(
            f"/api/artworks/{artwork_id}/annotations/{annotation_id}",
            headers=auth_headers,
            json={
                "category": "symbol",
                "text": "Updated note",
                "tags": ["symbol", "updated"],
                "linked_concept_names": ["migration"],
            },
        )

        assert patch_response.status_code == 200
        updated = patch_response.json()
        assert updated["category"] == "symbol"
        assert updated["text"] == "Updated note"
        assert updated["tags"] == ["symbol", "updated"]
        assert updated["linked_concept_names"] == ["migration"]


@pytest.mark.asyncio
async def test_move_pin_coordinates_persist_after_reload(
    auth_headers: dict[str, str],
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit_response = await client.post(
            "/api/visits",
            headers=auth_headers,
            json={
                "museum_name": "Move Pin Museum",
                "city": "Washington, DC",
                "visit_date": "2026-05-25",
            },
        )
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Move pin artwork", "visit_id": visit_response.json()["id"]},
        )
        artwork_id = artwork_response.json()["id"]

        create_response = await client.post(
            f"/api/artworks/{artwork_id}/annotations",
            headers=auth_headers,
            json={
                "x_percent": 10.0,
                "y_percent": 20.0,
                "category": "composition",
                "text": "Move me",
            },
        )
        annotation_id = create_response.json()["id"]

        move_response = await client.patch(
            f"/api/artworks/{artwork_id}/annotations/{annotation_id}",
            headers=auth_headers,
            json={"x_percent": 72.5, "y_percent": 18.0},
        )
        assert move_response.status_code == 200
        assert move_response.json()["x_percent"] == 72.5
        assert move_response.json()["y_percent"] == 18.0

        list_response = await client.get(f"/api/artworks/{artwork_id}/annotations")
        assert list_response.status_code == 200
        stored = list_response.json()[0]
        assert stored["x_percent"] == 72.5
        assert stored["y_percent"] == 18.0


@pytest.mark.asyncio
async def test_delete_annotation(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit_response = await client.post(
            "/api/visits",
            headers=auth_headers,
            json={
                "museum_name": "Delete Museum",
                "city": "Washington, DC",
                "visit_date": "2026-05-25",
            },
        )
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Delete annotation artwork", "visit_id": visit_response.json()["id"]},
        )
        artwork_id = artwork_response.json()["id"]

        create_response = await client.post(
            f"/api/artworks/{artwork_id}/annotations",
            headers=auth_headers,
            json={
                "x_percent": 50.0,
                "y_percent": 50.0,
                "category": "history",
                "text": "Delete me",
            },
        )
        annotation_id = create_response.json()["id"]

        delete_response = await client.delete(
            f"/api/artworks/{artwork_id}/annotations/{annotation_id}",
            headers=auth_headers,
        )
        assert delete_response.status_code == 204

        list_response = await client.get(f"/api/artworks/{artwork_id}/annotations")
        assert list_response.json() == []


@pytest.mark.asyncio
async def test_update_annotation_requires_auth() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            "/api/artworks/1/annotations/1",
            json={"text": "Hacked"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_annotation_requires_auth() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete("/api/artworks/1/annotations/1")

    assert response.status_code == 401
