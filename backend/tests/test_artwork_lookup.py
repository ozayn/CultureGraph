import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.sources.base import ArtworkLookupQuery
from app.sources.museums import is_nga_museum, is_smithsonian_museum
from app.sources.nga import search_nga_collection
from app.sources.smithsonian import search_smithsonian_collection


from app.sources.matching import is_placeholder_title


def test_is_placeholder_title_unknown() -> None:
    assert is_placeholder_title("Unknown")
    assert is_placeholder_title("untitled")
    assert not is_placeholder_title("Brooklyn Waterfront")


def test_resolve_search_terms_skips_placeholder_title() -> None:
    from app.sources.base import ArtworkLookupQuery
    from app.sources.matching import resolve_search_terms

    search_text, artist = resolve_search_terms(
        ArtworkLookupQuery(
            title="Unknown",
            artist="Botticelli",
            museum_name="National Gallery of Art",
            notes="waterfront bridge scene",
        )
    )
    assert search_text == "waterfront bridge scene"
    assert artist == "Botticelli"


@pytest.mark.asyncio
async def test_lookup_ignores_unknown_title_uses_notes(
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
                "title": "Unknown",
                "artist": "Botticelli",
                "personal_notes": "waterfront bridge scene",
                "visit_id": visit_id,
            },
        )
        artwork_id = artwork_response.json()["id"]

        lookup_response = await client.get(
            f"/api/artworks/{artwork_id}/lookup-image",
            headers=auth_headers,
            params={"source": "nga"},
        )

    payload = lookup_response.json()
    assert lookup_response.status_code == 200
    assert payload["query_source"] == "artist_notes"
    assert "waterfront" in payload["query_used"].lower()


@pytest.mark.asyncio
async def test_lookup_uses_ai_title_when_available(
    auth_headers: dict[str, str],
) -> None:
    from app.database import SessionLocal
    from app.models import ResearchNote

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
            json={"title": "Unknown", "artist": None, "visit_id": visit_id},
        )
        artwork_id = artwork_response.json()["id"]

        db = SessionLocal()
        try:
            db.add(
                ResearchNote(
                    artwork_id=artwork_id,
                    short_summary="Summary",
                    historical_context="Context",
                    visual_elements_to_notice="[]",
                    related_questions="[]",
                    suggested_annotations="[]",
                    possible_title="Brooklyn Waterfront",
                    possible_artist="John Doe",
                )
            )
            db.commit()
        finally:
            db.close()

        lookup_response = await client.get(
            f"/api/artworks/{artwork_id}/lookup-image",
            headers=auth_headers,
            params={"source": "nga"},
        )

    payload = lookup_response.json()
    assert payload["query_source"] == "ai_title"
    assert payload["query_used"].startswith("Brooklyn Waterfront")


@pytest.mark.asyncio
async def test_lookup_manual_title_override(
    auth_headers: dict[str, str],
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "Unknown", "artist": "Someone"},
        )
        artwork_id = artwork_response.json()["id"]

        lookup_response = await client.get(
            f"/api/artworks/{artwork_id}/lookup-image",
            headers=auth_headers,
            params={
                "source": "nga",
                "title_override": "The Adoration of the Magi",
                "artist_override": "Botticelli",
            },
        )

    payload = lookup_response.json()
    assert payload["query_source"] == "manual"
    assert "Adoration of the Magi" in payload["query_used"]


@pytest.mark.asyncio
async def test_apply_candidate_can_update_image_and_title(
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
            json={"title": "Unknown", "artist": "Botticelli", "visit_id": visit_id},
        )
        artwork_id = artwork_response.json()["id"]

        lookup_response = await client.get(
            f"/api/artworks/{artwork_id}/lookup-image",
            headers=auth_headers,
            params={"title_override": "The Adoration of the Magi", "artist_override": "Botticelli"},
        )
        candidate = lookup_response.json()["candidates"][0]

        update_response = await client.put(
            f"/api/artworks/{artwork_id}",
            headers=auth_headers,
            json={
                "image_url": candidate["image_url"],
                "image_thumbnail_url": candidate.get("image_thumbnail_url")
                or candidate["image_url"],
                "title": candidate["title"],
                "catalog_source": candidate["source_name"],
                "catalog_object_url": candidate["object_url"],
            },
        )

    updated = update_response.json()
    assert updated["title"] == candidate["title"]
    assert updated["title"] != "Unknown"
    assert updated["image_url"] == candidate["image_url"]


@pytest.mark.asyncio
async def test_lookup_falls_back_to_saved_title(
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

    payload = lookup_response.json()
    assert payload["query_source"] == "saved_title"
    assert "Adoration of the Magi" in payload["query_used"]


def test_is_nga_museum_recognizes_aliases() -> None:
    assert is_nga_museum("National Gallery of Art")
    assert is_nga_museum("national gallery of art, washington")
    assert not is_nga_museum("Smithsonian American Art Museum")


def test_is_smithsonian_museum_recognizes_aliases() -> None:
    assert is_smithsonian_museum("Smithsonian American Art Museum")
    assert is_smithsonian_museum("National Portrait Gallery")
    assert is_smithsonian_museum("Hirshhorn Museum and Sculpture Garden")
    assert is_smithsonian_museum("National Museum of Asian Art")
    assert not is_smithsonian_museum("National Gallery of Art")


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


def test_search_smithsonian_collection_finds_title_and_artist() -> None:
    results = search_smithsonian_collection(
        ArtworkLookupQuery(
            title="George Washington",
            artist="Ritchie",
            museum_name="Smithsonian American Art Museum",
        ),
        limit=5,
    )
    assert results
    assert "George Washington" in results[0].title
    assert results[0].image_url
    assert results[0].confidence >= 0.5
    assert "Smithsonian" in results[0].source_name or "Portrait" in results[0].source_name


def test_search_nga_skips_non_nga_museum_without_explicit_source() -> None:
    results = search_nga_collection(
        ArtworkLookupQuery(
            title="The Adoration of the Magi",
            artist="Botticelli",
            museum_name="The Met",
        )
    )
    assert results == []


def test_search_smithsonian_skips_non_smithsonian_museum_without_explicit_source() -> None:
    results = search_smithsonian_collection(
        ArtworkLookupQuery(
            title="George Washington",
            artist="Ritchie",
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


def test_search_smithsonian_explicit_source_overrides_museum() -> None:
    results = search_smithsonian_collection(
        ArtworkLookupQuery(
            title="George Washington",
            artist="Ritchie",
            museum_name="The Met",
            source="smithsonian",
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
async def test_lookup_image_endpoint_returns_smithsonian_candidates(
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
                "title": "George Washington",
                "artist": "Ritchie",
                "visit_id": visit_id,
            },
        )
        artwork_id = artwork_response.json()["id"]

        lookup_response = await client.get(
            f"/api/artworks/{artwork_id}/lookup-image",
            headers=auth_headers,
        )

    assert lookup_response.status_code == 200
    payload = lookup_response.json()
    assert payload["candidates"]
    assert "Smithsonian Open Access" in payload["sources_searched"]
    candidate = payload["candidates"][0]
    assert candidate["image_url"]
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
                "museum_name": "The Met",
                "city": "New York, NY",
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
async def test_lookup_image_with_source_param_searches_smithsonian(
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
                "title": "George Washington",
                "artist": "Ritchie",
                "visit_id": visit_id,
            },
        )
        artwork_id = artwork_response.json()["id"]

        lookup_response = await client.get(
            f"/api/artworks/{artwork_id}/lookup-image",
            headers=auth_headers,
            params={"source": "smithsonian"},
        )

    assert lookup_response.status_code == 200
    payload = lookup_response.json()
    assert payload["candidates"]
    assert "Smithsonian Open Access" in payload["sources_searched"]


@pytest.mark.asyncio
async def test_lookup_image_returns_notice_when_no_matches(
    auth_headers: dict[str, str],
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        artwork_response = await client.post(
            "/api/artworks",
            headers=auth_headers,
            json={"title": "ZZZ Nonexistent Artwork XYZ", "artist": "ZZZZZZ Nobody Known"},
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


@pytest.mark.asyncio
async def test_lookup_approximate_ai_title_returns_degas_matches(
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
                "title": "Four Dancers",
                "artist": "Edgar Degas",
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
    assert payload["query_strategy"] in {"exact", "fuzzy", "artist_fallback", "broad"}
    assert any("degas" in (c.get("artist") or "").lower() for c in payload["candidates"])
