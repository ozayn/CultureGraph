"""Visual artwork matching — embeddings, ranking, and API."""

from __future__ import annotations

import pytest
from PIL import Image

from app.models import CollectionArtwork, CollectionImageEmbedding, Visit
from app.services.visual_embedding import cosine_similarity, normalize_vector
from app.services.visual_matching import match_artwork_visually
from app.sources.museums import NGA_SOURCE_NAME


def test_cosine_similarity_identical_vectors() -> None:
    vector = normalize_vector([1.0, 2.0, 3.0, 0.5])
    assert cosine_similarity(vector, vector) == pytest.approx(1.0, abs=1e-5)


def test_cosine_similarity_orthogonal_vectors() -> None:
    left = normalize_vector([1.0, 0.0, 0.0])
    right = normalize_vector([0.0, 1.0, 0.0])
    assert cosine_similarity(left, right) == pytest.approx(0.0, abs=1e-5)


def test_visual_match_ranks_similar_embedding_first(db_session, tmp_path, monkeypatch) -> None:
    from app.models import Artwork
    from app.services import visual_embedding

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(visual_embedding.settings, "upload_dir", str(upload_dir))

    query_image = Image.new("RGB", (64, 64), color=(180, 40, 40))
    query_path = upload_dir / "query.webp"
    query_image.save(query_path, format="WEBP")
    query_vector = visual_embedding.embed_pil_image(query_image)

    dance_vector = query_vector
    portrait_vector = normalize_vector([1.0 if index % 2 else -1.0 for index in range(128)])

    dance = _seed_collection_record(
        db_session,
        object_id="dance-1",
        title="Ballet Rehearsal",
        artist="Edgar Degas",
        vector=dance_vector,
    )
    _seed_collection_record(
        db_session,
        object_id="portrait-1",
        title="Portrait of a Man",
        artist="Edgar Degas",
        vector=portrait_vector,
    )
    db_session.commit()

    visit = Visit(museum_name="National Gallery of Art", city="Washington", visit_date="2026-01-01")
    db_session.add(visit)
    db_session.flush()
    artwork = Artwork(
        title="Unknown",
        visit_id=visit.id,
        image_url="/uploads/query.webp",
    )
    db_session.add(artwork)
    db_session.commit()

    result = match_artwork_visually(db_session, artwork)
    assert result.index_status == "ready"
    assert result.candidates
    assert result.candidates[0].title == dance.title
    assert result.candidates[0].external_id == "dance-1"
    assert result.candidates[0].similarity_score >= result.candidates[-1].similarity_score


def test_visual_match_missing_image_returns_notice(db_session) -> None:
    from app.models import Artwork

    visit = Visit(museum_name="National Gallery of Art", city="Washington", visit_date="2026-01-01")
    db_session.add(visit)
    db_session.flush()
    artwork = Artwork(title="Unknown", visit_id=visit.id, image_url=None)
    db_session.add(artwork)
    db_session.commit()

    result = match_artwork_visually(db_session, artwork)
    assert result.candidates == []
    assert result.notice
    assert "Upload a photo" in result.notice


def test_visual_match_empty_index_returns_build_notice(db_session, tmp_path, monkeypatch) -> None:
    from app.models import Artwork
    from app.services import visual_embedding

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(visual_embedding.settings, "upload_dir", str(upload_dir))
    query_path = upload_dir / "query.webp"
    Image.new("RGB", (32, 32), color=(100, 100, 100)).save(query_path, format="WEBP")

    visit = Visit(museum_name="National Gallery of Art", city="Washington", visit_date="2026-01-01")
    db_session.add(visit)
    db_session.flush()
    artwork = Artwork(title="Unknown", visit_id=visit.id, image_url="/uploads/query.webp")
    db_session.add(artwork)
    db_session.commit()

    result = match_artwork_visually(db_session, artwork)
    assert result.index_status == "empty"
    assert result.notice
    assert "Visual index not built yet" in result.notice


def test_visual_match_endpoint(db_session, auth_headers, tmp_path, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from app.main import app
    from app.models import Artwork
    from app.services import visual_embedding

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(visual_embedding.settings, "upload_dir", str(upload_dir))
    image = Image.new("RGB", (48, 48), color=(90, 120, 60))
    image.save(upload_dir / "art.webp", format="WEBP")
    vector = visual_embedding.embed_pil_image(image)

    _seed_collection_record(
        db_session,
        object_id="match-1",
        title="Green Landscape",
        artist="Unknown",
        vector=vector,
    )
    visit = Visit(museum_name="National Gallery of Art", city="Washington", visit_date="2026-01-01")
    db_session.add(visit)
    db_session.flush()
    artwork = Artwork(title="Unknown", visit_id=visit.id, image_url="/uploads/art.webp")
    db_session.add(artwork)
    db_session.commit()

    client = TestClient(app)
    response = client.post(f"/api/artworks/{artwork.id}/visual-match", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["index_status"] == "ready"
    assert payload["candidates"]
    assert payload["candidates"][0]["title"] == "Green Landscape"


def _seed_collection_record(
    db_session,
    *,
    object_id: str,
    title: str,
    artist: str,
    vector: list[float],
) -> CollectionArtwork:
    from app.services.visual_embedding import EMBEDDING_MODEL_KEY

    record = CollectionArtwork(
        source_name=NGA_SOURCE_NAME,
        source_object_id=object_id,
        title=title,
        artist=artist,
        date="1900",
        medium="oil on canvas",
        image_url="https://example.org/image.jpg",
        thumbnail_url="https://example.org/thumb.jpg",
        object_url=f"https://example.org/object/{object_id}",
        rights_label="CC0",
    )
    db_session.add(record)
    db_session.flush()
    db_session.add(
        CollectionImageEmbedding(
            collection_artwork_id=record.id,
            embedding_model=EMBEDDING_MODEL_KEY,
            embedding_vector=vector,
            image_url=record.thumbnail_url,
        )
    )
    return record
