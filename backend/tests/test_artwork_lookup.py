import pytest

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
