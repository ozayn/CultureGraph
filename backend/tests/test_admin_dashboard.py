import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.jwt import create_access_token
from app.main import app


@pytest.fixture
def non_admin_headers() -> dict[str, str]:
    token = create_access_token("stranger@example.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_admin_summary_requires_auth() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/admin/summary")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_summary_rejects_non_admin_user(non_admin_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/admin/summary", headers=non_admin_headers)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_summary_returns_counts(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/visits",
            headers=auth_headers,
            json={
                "museum_name": "Admin Dashboard Museum",
                "city": "Washington, DC",
                "visit_date": "2026-05-25",
            },
        )
        response = await client.get("/api/admin/summary", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["visits"] >= 1
    assert "artworks" in payload
    assert "annotations" in payload
    assert "cultural_entities" in payload
    assert "research_notes" in payload


@pytest.mark.asyncio
async def test_admin_visits_supports_search_and_pagination(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/visits",
            headers=auth_headers,
            json={
                "museum_name": "Unique Admin Search Museum",
                "city": "Washington, DC",
                "visit_date": "2026-05-25",
            },
        )

        list_response = await client.get(
            "/api/admin/visits",
            headers=auth_headers,
            params={"search": "Unique Admin Search", "limit": 10, "offset": 0},
        )

    assert list_response.status_code == 200
    payload = list_response.json()
    assert payload["meta"]["total"] >= 1
    assert payload["meta"]["limit"] == 10
    assert payload["meta"]["search"] == "Unique Admin Search"
    assert any("Unique Admin Search" in item["museum_name"] for item in payload["records"])


@pytest.mark.asyncio
async def test_admin_artworks_list(auth_headers: dict[str, str]) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/admin/artworks", headers=auth_headers, params={"limit": 5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"]["limit"] == 5
    assert isinstance(payload["records"], list)
