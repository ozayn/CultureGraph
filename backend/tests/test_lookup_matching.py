"""Tests for fuzzy and staged museum lookup matching."""

from app.services.artwork_lookup import lookup_artwork_candidates
from app.sources.base import ArtworkLookupQuery
from app.sources.matching import title_similarity, token_overlap


def test_token_overlap_matches_dancer_variants() -> None:
    assert token_overlap("Four Dancers", "Little Dancer Aged Fourteen") > 0


def test_title_similarity_fuzzy_for_approximate_titles() -> None:
    score = title_similarity("Four Dancers", "Little Dancer Aged Fourteen")
    assert score >= 0.35


def test_lookup_four_dancers_degas_returns_nga_matches() -> None:
    query = ArtworkLookupQuery(
        title="Four Dancers",
        artist="Edgar Degas",
        museum_name="National Gallery of Art",
        has_title_query=True,
    )
    result = lookup_artwork_candidates(query)
    assert result.candidates
    assert result.query_strategy in {"exact", "fuzzy", "artist_fallback", "broad"}
    titles = " ".join(candidate.title.lower() for candidate in result.candidates)
    assert "dancer" in titles or "degas" in titles.lower()
    degas_hits = [c for c in result.candidates if c.artist and "degas" in c.artist.lower()]
    assert len(degas_hits) >= 3


def test_lookup_artist_fallback_strategy_when_title_absent_in_index() -> None:
    query = ArtworkLookupQuery(
        title="Nonexistent Ballet Rehearsal Scene",
        artist="Edgar Degas",
        museum_name="National Gallery of Art",
        has_title_query=True,
    )
    result = lookup_artwork_candidates(query)
    assert result.candidates
    assert result.query_strategy is not None
    assert any("degas" in (c.artist or "").lower() for c in result.candidates)
