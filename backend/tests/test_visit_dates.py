"""Visit dates are calendar dates without timezone shifting."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_visit_date_roundtrip_preserves_calendar_day(
    auth_headers: dict[str, str],
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_response = await client.post(
            "/api/visits",
            headers=auth_headers,
            json={
                "museum_name": "Test Museum",
                "city": "Washington, DC",
                "visit_date": "2026-05-23",
            },
        )
        assert create_response.status_code == 201
        payload = create_response.json()
        visit_id = payload["id"]
        assert payload["visit_date"] == "2026-05-23"

        get_response = await client.get(f"/api/visits/{visit_id}")
        assert get_response.status_code == 200
        assert get_response.json()["visit_date"] == "2026-05-23"

        update_response = await client.patch(
            f"/api/visits/{visit_id}",
            headers=auth_headers,
            json={"visit_date": "2026-05-24"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["visit_date"] == "2026-05-24"
