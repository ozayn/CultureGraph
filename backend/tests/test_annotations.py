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
