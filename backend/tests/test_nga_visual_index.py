"""Tests for NGA visual index builder helpers."""

from __future__ import annotations

import json
from io import BytesIO

import pytest
from PIL import Image

from app.services import nga_visual_index
from app.services.visual_embedding import EMBEDDING_MODEL_KEY


def test_resolve_start_offset_uses_saved_state(tmp_path, monkeypatch) -> None:
    state_file = tmp_path / "nga_visual_index_state.json"
    state_file.write_text(
        json.dumps(
            {
                "embedding_model": EMBEDDING_MODEL_KEY,
                "next_offset": 250,
                "updated_at": "2026-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(nga_visual_index, "STATE_FILE", state_file)

    offset = nga_visual_index.resolve_start_offset(
        nga_visual_index.BuildOptions(
            limit=100,
            resume=True,
            rebuild=False,
            batch_size=25,
            dry_run=False,
        )
    )
    assert offset == 250


def test_resolve_start_offset_ignores_mismatched_model(tmp_path, monkeypatch) -> None:
    state_file = tmp_path / "nga_visual_index_state.json"
    state_file.write_text(
        json.dumps(
            {
                "embedding_model": "other-model:weights",
                "next_offset": 250,
                "updated_at": "2026-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(nga_visual_index, "STATE_FILE", state_file)

    offset = nga_visual_index.resolve_start_offset(
        nga_visual_index.BuildOptions(
            limit=100,
            resume=True,
            rebuild=False,
            batch_size=25,
            dry_run=False,
        )
    )
    assert offset == 0


def test_load_thumbnail_uses_cache(tmp_path, monkeypatch) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    monkeypatch.setattr(nga_visual_index, "THUMBNAIL_CACHE_DIR", cache_dir)

    image = Image.new("RGB", (24, 24), color=(10, 20, 30))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    cache_path = cache_dir / "obj-1.jpg"
    cache_path.write_bytes(buffer.getvalue())

    loaded, cache_hit = nga_visual_index.load_thumbnail("obj-1", "https://example.org/missing.jpg", dry_run=False)
    assert cache_hit is True
    assert loaded is not None
    assert loaded.size == (24, 24)


def test_run_build_dry_run_does_not_write_state(tmp_path, monkeypatch, db_session) -> None:
    lookup_file = tmp_path / "nga_lookup_index.json"
    lookup_file.write_text(
        json.dumps(
            [
                {
                    "object_id": "1",
                    "title": "Test Artwork",
                    "image_thumbnail_url": "https://example.org/thumb.jpg",
                }
            ]
        ),
        encoding="utf-8",
    )
    state_file = tmp_path / "nga_visual_index_state.json"
    monkeypatch.setattr(nga_visual_index, "NGA_LOOKUP_INDEX", lookup_file)
    monkeypatch.setattr(nga_visual_index, "STATE_FILE", state_file)

    metrics = nga_visual_index.run_build(
        db=db_session,
        options=nga_visual_index.BuildOptions(
            limit=1,
            resume=False,
            rebuild=False,
            batch_size=1,
            dry_run=True,
        ),
    )
    assert metrics.processed == 1
    assert metrics.new_embeddings == 1
    assert not state_file.exists()
