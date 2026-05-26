import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.sources.base import ArtworkLookupQuery
from app.sources.nga import is_nga_museum, search_nga_collection


def test_is_nga_museum_recognizes_aliases() -> None:
    assert is_nga_museum("National Gallery of Art")
    assert is_nga_museum("national gallery of art, washington")
    assert not is_nga_museum("Smithsonian American Art Museum")


def test_search_nga_collection_finds_title_and_artist() -> None:
    results = search_nga_collection(
        ArtworkLookupQuery(
            title="The Adoration of the Magi",
            artist="Botticelli",
            museum_name="National Gallery of Art",
        ),
        limit=5,
    )
    assert results
    assert results[0].title == "The Adoration of the Magi"
    assert results[0].image_url
    assert results[0].confidence >= 0.5
    assert results[0].source_name == "National Gallery of Art"


def test_search_nga_skips_non_nga_museum_without_explicit_source() -> None:
    results = search_nga_collection(
        ArtworkLookupQuery(
            title="The Adoration of the Magi",
            artist="Botticelli",
            museum_name="The Met",
        )
    )
    assert results == []


def test_search_nga_explicit_source_overrides_museum() -> None:
    results = search_nga_collection(
        ArtworkLookupQuery(
            title="The Adoration of the Magi",
            artist="Botticelli",
            museum_name="The Met",
            source="nga",
        ),
        limit=3,
    )
    assert results


@pytest.mark.asyncio
async def test_lookup_image_endpoint_requires_auth() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/artworks/1/lookup-image")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_lookup_image_endpoint_returns_nga_candidates(
    auth_headers: dict[str, str],
) -> None:
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
        assert visit_response.status_code == 201
        visit_id = visit_response.json()["id"]

        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={
                "title": "The Adoration of the Magi",
                "artist": "Botticelli",
                "visit_id": visit_id,
            },
        )
        assert artwork_response.status_code == 201
        artwork_id = artwork_response.json()["id"]

        lookup_response = await client.get(
            f"/api/artworks/{artwork_id}/lookup-image",
            headers=auth_headers,
        )

    assert lookup_response.status_code == 200
    payload = lookup_response.json()
    assert payload["candidates"]
    assert "National Gallery of Art" in payload["sources_searched"]
    candidate = payload["candidates"][0]
    assert candidate["image_url"]
    assert candidate.get("image_thumbnail_url")
    assert candidate["source_name"] == "National Gallery of Art"
    assert candidate["confidence"] > 0


@pytest.mark.asyncio
async def test_apply_official_image_persists_url_and_catalog_metadata(
    auth_headers: dict[str, str],
) -> None:
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

        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={
                "title": "The Adoration of the Magi",
                "artist": "Botticelli",
                "visit_id": visit_id,
            },
        )
        artwork_id = artwork_response.json()["id"]

        lookup_response = await client.get(
            f"/api/artworks/{artwork_id}/lookup-image",
            headers=auth_headers,
        )
        candidate = lookup_response.json()["candidates"][0]

        update_response = await client.put(
            f"/api/artworks/{artwork_id}",
            headers=auth_headers,
            json={
                "image_url": candidate["image_url"],
                "image_thumbnail_url": candidate.get("image_thumbnail_url")
                or candidate["image_url"],
                "catalog_source": candidate["source_name"],
                "catalog_object_url": candidate["object_url"],
                "catalog_accession_number": candidate["accession_number"],
                "catalog_rights_label": candidate["rights_label"],
            },
        )
        assert update_response.status_code == 200
        updated = update_response.json()

        get_response = await client.get(f"/api/artworks/{artwork_id}")

    assert updated["image_url"] == candidate["image_url"]
    assert updated["image_thumbnail_url"] == (
        candidate.get("image_thumbnail_url") or candidate["image_url"]
    )
    assert updated["catalog_source"] == candidate["source_name"]
    assert updated["catalog_object_url"] == candidate["object_url"]
    assert get_response.json()["image_thumbnail_url"] == updated["image_thumbnail_url"]


@pytest.mark.asyncio
async def test_lookup_image_unsupported_museum_returns_empty(
    auth_headers: dict[str, str],
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit_response = await client.post(
            "/api/visits",
            headers=auth_headers,
            json={
                "museum_name": "Smithsonian American Art Museum",
                "city": "Washington, DC",
                "visit_date": "2026-05-25",
            },
        )
        visit_id = visit_response.json()["id"]

        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Some artwork", "visit_id": visit_id},
        )
        artwork_id = artwork_response.json()["id"]

        lookup_response = await client.get(
            f"/api/artworks/{artwork_id}/lookup-image",
            headers=auth_headers,
        )

    assert lookup_response.status_code == 200
    payload = lookup_response.json()
    assert payload["candidates"] == []
    assert payload["sources_searched"] == []


@pytest.mark.asyncio
async def test_lookup_image_with_source_param_searches_nga(
    auth_headers: dict[str, str],
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        visit_response = await client.post(
            "/api/visits",
            headers=auth_headers,
            json={
                "museum_name": "Smithsonian American Art Museum",
                "city": "Washington, DC",
                "visit_date": "2026-05-25",
            },
        )
        visit_id = visit_response.json()["id"]

        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={
                "title": "The Adoration of the Magi",
                "artist": "Botticelli",
                "visit_id": visit_id,
            },
        )
        artwork_id = artwork_response.json()["id"]

        lookup_response = await client.get(
            f"/api/artworks/{artwork_id}/lookup-image",
            headers=auth_headers,
            params={"source": "nga"},
        )

    assert lookup_response.status_code == 200
    payload = lookup_response.json()
    assert payload["candidates"]
    assert "National Gallery of Art" in payload["sources_searched"]


@pytest.mark.asyncio
async def test_lookup_image_returns_notice_when_no_matches(
    auth_headers: dict[str, str],
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "ZZZ Nonexistent Artwork XYZ", "artist": "Nobody Known"},
        )
        artwork_id = artwork_response.json()["id"]

        lookup_response = await client.get(
            f"/api/artworks/{artwork_id}/lookup-image",
            headers=auth_headers,
            params={"source": "nga"},
        )

    assert lookup_response.status_code == 200
    payload = lookup_response.json()
    assert payload["candidates"] == []
    assert payload["notice"]
