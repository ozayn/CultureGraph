import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.jwt import create_access_token
from app.main import app


@pytest.fixture
def non_admin_headers() -> dict[str, str]:
    token = create_access_token("stranger@example.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_bulk_delete_requires_auth() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/admin/visits/bulk-delete", json={"ids": [1]})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_bulk_delete_rejects_non_admin_user(non_admin_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/visits/bulk-delete",
            headers=non_admin_headers,
            json={"ids": [1]},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_bulk_delete_visits_cascades_children(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit_response = await client.post(
            "/api/visits",
            headers=auth_headers,
            json={
                "museum_name": "Bulk Delete Museum",
                "city": "Washington, DC",
                "visit_date": "2026-05-25",
            },
        )
        visit_id = visit_response.json()["id"]

        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"visit_id": visit_id, "title": "Bulk Delete Artwork"},
        )
        artwork_id = artwork_response.json()["id"]

        await client.post(
            f"/api/artworks/{artwork_id}/annotations",
            headers=auth_headers,
            json={
                "x_percent": 10,
                "y_percent": 20,
                "category": "observation",
                "text": "Bulk delete annotation",
            },
        )

        summary_before = await client.get("/api/admin/summary", headers=auth_headers)
        before = summary_before.json()

        delete_response = await client.post(
            "/api/admin/visits/bulk-delete",
            headers=auth_headers,
            json={"ids": [visit_id]},
        )

        summary_after = await client.get("/api/admin/summary", headers=auth_headers)
        after = summary_after.json()

    assert delete_response.status_code == 200
    assert delete_response.json()["deleted_count"] == 1
    assert after["visits"] == before["visits"] - 1
    assert after["artworks"] <= before["artworks"] - 1
    assert after["annotations"] <= before["annotations"] - 1


@pytest.mark.asyncio
async def test_bulk_delete_artworks_removes_annotations(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Bulk Delete Artwork Only"},
        )
        artwork_id = artwork_response.json()["id"]

        await client.post(
            f"/api/artworks/{artwork_id}/annotations",
            headers=auth_headers,
            json={
                "x_percent": 5,
                "y_percent": 15,
                "category": "history",
                "text": "Annotation to remove",
            },
        )

        delete_response = await client.post(
            "/api/admin/artworks/bulk-delete",
            headers=auth_headers,
            json={"ids": [artwork_id]},
        )

        annotations_list = await client.get(
            f"/api/artworks/{artwork_id}/annotations",
            headers=auth_headers,
        )

    assert delete_response.status_code == 200
    assert delete_response.json()["deleted_count"] == 1
    assert annotations_list.status_code == 404


@pytest.mark.asyncio
async def test_bulk_delete_reports_missing_ids(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/annotations/bulk-delete",
            headers=auth_headers,
            json={"ids": [999_999_999]},
        )

    assert response.status_code == 404
    assert "999999999" in response.json()["detail"]


@pytest.mark.asyncio
async def test_bulk_delete_rejects_empty_ids(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/admin/entities/bulk-delete",
            headers=auth_headers,
            json={"ids": []},
        )

    assert response.status_code == 422
