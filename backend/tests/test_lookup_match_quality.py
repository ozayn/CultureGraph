"""Tests for strict official collection match filtering."""

from __future__ import annotations

from app.services.lookup_ranking import partition_lookup_candidates, rank_lookup_candidates
from app.sources.base import ArtworkLookupCandidate, ArtworkLookupQuery
from app.sources.matching import (
    artist_similarity,
    meaningful_title_overlap,
    passes_title_specific_gate,
)


def _candidate(title: str, artist: str | None = None) -> ArtworkLookupCandidate:
    return ArtworkLookupCandidate(
        title=title,
        artist=artist,
        date=None,
        medium="oil on canvas",
        image_url="https://example.org/image.jpg",
        image_thumbnail_url="https://example.org/thumb.jpg",
        object_url="https://example.org/object",
        accession_number="1",
        source_name="National Gallery of Art",
        confidence=0.5,
        rights_label="CC0",
        external_id="1",
    )


def test_jacques_callot_not_matched_to_jacques_louis_david() -> None:
    score = artist_similarity("Jacques-Louis David", "Jacques Callot")
    assert score < 0.35


def test_napoleon_title_overlap_excludes_unrelated_portrait() -> None:
    query = "The Emperor Napoleon in His Study at the Tuileries"
    unrelated = "Portrait of a Young Woman in White"
    overlap = meaningful_title_overlap(query, unrelated)
    assert overlap < 0.15


def test_napoleon_query_filters_unrelated_candidates() -> None:
    query = ArtworkLookupQuery(
        title="The Emperor Napoleon in His Study at the Tuileries",
        artist="Jacques-Louis David",
        museum_name="National Gallery of Art",
        has_title_query=True,
        source="nga",
    )
    raw = [
        (
            0.62,
            {"title": "Portrait of a Young Woman in White", "artist": "Unknown"},
            _candidate("Portrait of a Young Woman in White", "Unknown"),
        ),
        (
            0.58,
            {"title": "The Trench", "artist": "Unknown"},
            _candidate("The Trench", "Unknown"),
        ),
        (
            0.91,
            {
                "title": "The Emperor Napoleon in His Study at the Tuileries",
                "artist": "Jacques-Louis David",
            },
            _candidate(
                "The Emperor Napoleon in His Study at the Tuileries",
                "Jacques-Louis David",
            ),
        ),
        (
            0.55,
            {"title": "Portrait Study", "artist": "Jacques Callot"},
            _candidate("Portrait Study", "Jacques Callot"),
        ),
    ]

    ranked = rank_lookup_candidates(raw, query, strategy="exact")
    primary, related = partition_lookup_candidates(ranked)

    assert primary
    assert primary[0].title == "The Emperor Napoleon in His Study at the Tuileries"
    assert all("Callot" not in (item.artist or "") for item in primary)
    assert all("Young Woman" not in item.title for item in primary)
    assert not any("Callot" in (item.artist or "") for item in primary)


def test_circle_of_artist_is_weak_not_primary_match() -> None:
    query = ArtworkLookupQuery(
        title="The Emperor Napoleon in His Study at the Tuileries",
        artist="Jacques-Louis David",
        museum_name="National Gallery of Art",
        has_title_query=True,
        source="nga",
    )
    raw = [
        (
            0.66,
            {
                "title": "Portrait of Napoleon",
                "artist": "Circle of Jacques-Louis David",
            },
            _candidate("Portrait of Napoleon", "Circle of Jacques-Louis David"),
        ),
    ]

    ranked = rank_lookup_candidates(raw, query, strategy="fuzzy")
    primary, related = partition_lookup_candidates(ranked)

    assert not primary
    assert related
    assert related[0].match_tier == "weak"


def test_all_weak_candidates_yield_no_primary_matches() -> None:
    query = ArtworkLookupQuery(
        title="The Emperor Napoleon in His Study at the Tuileries",
        artist="Jacques-Louis David",
        museum_name="National Gallery of Art",
        has_title_query=True,
        source="nga",
    )
    raw = [
        (
            0.44,
            {"title": "Landscape with Bridge", "artist": "Unknown"},
            _candidate("Landscape with Bridge", "Unknown"),
        ),
        (
            0.41,
            {"title": "The Trench", "artist": "Unknown"},
            _candidate("The Trench", "Unknown"),
        ),
    ]

    ranked = rank_lookup_candidates(raw, query, strategy="exact")
    primary, related = partition_lookup_candidates(ranked)

    assert not primary
    assert not related


def test_passes_title_specific_gate_rejects_wrong_artist() -> None:
    allowed = passes_title_specific_gate(
        search_text="The Emperor Napoleon in His Study at the Tuileries",
        artist_text="Jacques-Louis David",
        entry={"title": "Portrait Study", "artist": "Jacques Callot"},
        title_score=0.2,
        artist_score=artist_similarity("Jacques-Louis David", "Jacques Callot"),
    )
    assert not allowed
