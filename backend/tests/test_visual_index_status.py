"""Admin visual index status endpoint."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.visual_embedding import EMBEDDING_MODEL_KEY
from app.sources.museums import NGA_SOURCE_NAME


@pytest.mark.asyncio
async def test_visual_index_status_requires_auth() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/admin/visual-index-status")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_visual_index_status_returns_counts(
    auth_headers: dict[str, str],
    db_session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    from app.models import CollectionArtwork, CollectionImageEmbedding
    from app.services import visual_index_status

    monkeypatch.setattr(visual_index_status, "THUMBNAIL_CACHE_DIR", tmp_path / "cache")

    record = CollectionArtwork(
        source_name=NGA_SOURCE_NAME,
        source_object_id="status-1",
        title="Status Test",
        artist="Artist",
        thumbnail_url="https://example.org/thumb.jpg",
    )
    db_session.add(record)
    db_session.flush()
    db_session.add(
        CollectionImageEmbedding(
            collection_artwork_id=record.id,
            embedding_model=EMBEDDING_MODEL_KEY,
            embedding_vector=[0.1, 0.2, 0.3],
            image_url=record.thumbnail_url,
        )
    )
    db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/admin/visual-index-status", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["indexed_count"] == 1
    assert payload["embedding_model"] == EMBEDDING_MODEL_KEY
    assert payload["source_name"] == NGA_SOURCE_NAME
    assert payload["thumbnail_cache_size"] == 0
    assert payload["last_updated"]
