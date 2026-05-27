"""Tests for medium-type classification and lookup ranking."""

from app.services.artwork_lookup import lookup_artwork_candidates
from app.services.lookup_medium import (
    classify_medium,
    infer_expected_medium_type,
    medium_score_adjustment,
)
from app.sources.base import ArtworkLookupQuery


def _all_matches(result):
    return [*result.candidates, *result.related_candidates]


def test_classify_medium_painting_is_2d() -> None:
    assert classify_medium("oil on canvas") == "2d"
    assert classify_medium("pastel on paper") == "2d"
    assert classify_medium("charcoal on buff wove paper") == "2d"


def test_classify_medium_sculpture_is_3d() -> None:
    assert classify_medium("painted plaster, fabric, metal armature") == "3d"
    assert classify_medium("pigmented beeswax, plastiline, metal armature") == "3d"


def test_infer_expected_medium_from_artwork_or_ai() -> None:
    assert (
        infer_expected_medium_type(
            artwork_medium=None,
            ai_medium="pastel on paper",
        )
        == "2d"
    )
    assert (
        infer_expected_medium_type(
            artwork_medium="bronze sculpture",
            ai_medium="pastel",
        )
        == "3d"
    )


def test_medium_score_adjustment_boosts_matches_penalizes_mismatch() -> None:
    assert medium_score_adjustment("2d", "2d") > 0
    assert medium_score_adjustment("2d", "3d") < 0


def test_degas_pastel_query_ranks_2d_above_little_dancer_sculpture() -> None:
    query = ArtworkLookupQuery(
        title="Four Dancers",
        artist="Edgar Degas",
        museum_name="National Gallery of Art",
        has_title_query=True,
        expected_medium_type="2d",
        medium_type_filter="any",
        source="nga",
    )
    result = lookup_artwork_candidates(query)
    matches = _all_matches(result)
    assert matches

    titles = [candidate.title for candidate in matches]
    match_titles = [candidate.title for candidate in matches]
    assert "Little Dancer Aged Fourteen" in match_titles
    assert any("Girl in Red" == title or "Woman Ironing" == title for title in titles)

    dancer_idx = match_titles.index("Little Dancer Aged Fourteen")
    two_d_indices = [
        titles.index(title)
        for title in titles
        if title in {"Girl in Red", "Woman Ironing", "Three Studies of Ludovic Halévy Standing"}
    ]
    assert two_d_indices
    assert min(two_d_indices) < dancer_idx

    dancer = next(c for c in matches if c.title == "Little Dancer Aged Fourteen")
    assert dancer.medium_match is False
    assert dancer.medium_type == "3d"
    assert any("Medium mismatch" in reason for reason in dancer.match_reasons)


def test_medium_type_any_returns_sculptures_and_2d() -> None:
    query = ArtworkLookupQuery(
        title="Four Dancers",
        artist="Edgar Degas",
        museum_name="National Gallery of Art",
        has_title_query=True,
        expected_medium_type="2d",
        medium_type_filter="any",
        source="nga",
    )
    result = lookup_artwork_candidates(query)
    mediums = {candidate.medium_type for candidate in _all_matches(result)}
    assert "2d" in mediums
    assert "3d" in mediums


def test_medium_type_3d_filter_returns_sculptures_only() -> None:
    query = ArtworkLookupQuery(
        title="Four Dancers",
        artist="Edgar Degas",
        museum_name="National Gallery of Art",
        has_title_query=True,
        expected_medium_type="2d",
        medium_type_filter="3d",
        source="nga",
    )
    result = lookup_artwork_candidates(query)
    matches = _all_matches(result)
    assert matches
    assert all(candidate.medium_type == "3d" for candidate in matches)
    assert any("Dancer" in candidate.title for candidate in matches)
