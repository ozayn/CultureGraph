"""Tests for Met, AIC, and Wikimedia lookup adapters."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.sources.aic import collect_aic_scored_candidates, search_aic_collection
from app.sources.base import ArtworkLookupQuery
from app.sources.met import collect_met_scored_candidates, search_met_collection
from app.sources.museums import is_aic_museum, is_met_museum
from app.sources.routing import resolve_lookup_sources, sources_searched_labels
from app.sources.wikimedia import collect_wikimedia_scored_candidates
from app.services.lookup_stages import lookup_artwork_candidates_staged


def test_is_met_museum_recognizes_aliases() -> None:
    assert is_met_museum("The Met")
    assert is_met_museum("Metropolitan Museum of Art")
    assert not is_met_museum("National Gallery of Art")


def test_is_aic_museum_recognizes_aliases() -> None:
    assert is_aic_museum("Art Institute of Chicago")
    assert is_aic_museum("AIC")
    assert not is_aic_museum("The Met")


def test_resolve_lookup_sources_for_met_visit() -> None:
    sources = resolve_lookup_sources(
        ArtworkLookupQuery(title="Portrait", artist="Rembrandt", museum_name="The Met")
    )
    assert sources == ["met"]


def test_resolve_lookup_sources_all_includes_museums() -> None:
    sources = resolve_lookup_sources(
        ArtworkLookupQuery(title="Portrait", artist="Rembrandt", museum_name=None, source="all")
    )
    assert "nga" in sources
    assert "smithsonian" in sources
    assert "met" in sources
    assert "aic" in sources


def test_sources_searched_labels_include_new_museums() -> None:
    labels = sources_searched_labels(
        ArtworkLookupQuery(title="Test", artist=None, museum_name="The Met", source="all")
    )
    assert "The Metropolitan Museum of Art" in labels
    assert "Art Institute of Chicago" in labels


@patch("app.sources.met.requests.get")
def test_search_met_collection_maps_api_results(mock_get: MagicMock) -> None:
    search_response = MagicMock()
    search_response.raise_for_status.return_value = None
    search_response.json.return_value = {"objectIDs": [12345]}

    object_response = MagicMock()
    object_response.raise_for_status.return_value = None
    object_response.json.return_value = {
        "objectID": 12345,
        "title": "Washington Crossing the Delaware",
        "artistDisplayName": "Emanuel Leutze",
        "objectDate": "1851",
        "medium": "Oil on canvas",
        "primaryImage": "https://images.metmuseum.org/CRDImages/ad/original/DT1854.jpg",
        "primaryImageSmall": "https://images.metmuseum.org/CRDImages/ad/web-large/DT1854.jpg",
        "objectURL": "https://www.metmuseum.org/art/collection/search/12345",
        "accessionNumber": "97.34",
        "isPublicDomain": True,
    }

    mock_get.side_effect = [search_response, object_response]

    results = search_met_collection(
        ArtworkLookupQuery(
            title="Washington Crossing the Delaware",
            artist="Leutze",
            museum_name="The Met",
            source="met",
            has_title_query=True,
        ),
        limit=3,
    )

    assert results
    assert results[0].title == "Washington Crossing the Delaware"
    assert results[0].image_url
    assert results[0].object_url
    assert results[0].source_name == "The Metropolitan Museum of Art"


@patch("app.sources.aic.requests.get")
def test_search_aic_collection_maps_api_results(mock_get: MagicMock) -> None:
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "data": [
            {
                "id": 16564,
                "title": "A Sunday on La Grande Jatte",
                "artist_display": "Georges Seurat",
                "date_display": "1884–1886",
                "medium_display": "Oil on canvas",
                "image_id": "00000000-0000-0000-0000-000000000001",
                "is_public_domain": True,
            }
        ]
    }
    mock_get.return_value = response

    results = search_aic_collection(
        ArtworkLookupQuery(
            title="Sunday on La Grande Jatte",
            artist="Seurat",
            museum_name="Art Institute of Chicago",
            source="aic",
        ),
        limit=3,
    )

    assert results
    assert "Grande Jatte" in results[0].title
    assert results[0].image_url
    assert "artic.edu/artworks/16564" in (results[0].object_url or "")
    assert results[0].source_name == "Art Institute of Chicago"


@patch("app.sources.wikimedia.requests.get")
def test_wikimedia_fallback_returns_commons_candidate(mock_get: MagicMock) -> None:
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "query": {
            "pages": {
                "1": {
                    "pageid": 1,
                    "title": "File:Example Portrait.jpg",
                    "canonicalurl": "https://commons.wikimedia.org/wiki/File:Example_Portrait.jpg",
                    "imageinfo": [
                        {
                            "url": "https://upload.wikimedia.org/wikipedia/commons/1/1e/Example_Portrait.jpg",
                            "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Example_Portrait.jpg/400px-Example_Portrait.jpg",
                            "mime": "image/jpeg",
                            "descriptionurl": "https://commons.wikimedia.org/wiki/File:Example_Portrait.jpg",
                            "extmetadata": {
                                "Artist": {"value": "Example Artist"},
                                "LicenseShortName": {"value": "Public domain"},
                            },
                        }
                    ],
                }
            }
        }
    }
    mock_get.return_value = response

    scored = collect_wikimedia_scored_candidates(
        ArtworkLookupQuery(
            title="Example Portrait",
            artist="Example Artist",
            museum_name="The Met",
            source="wikimedia",
        )
    )

    assert scored
    assert scored[0][2].source_name == "Wikimedia Commons"
    assert scored[0][2].object_url


@patch("app.services.lookup_stages.collect_met_scored_candidates", return_value=[])
@patch("app.services.lookup_stages.collect_nga_scored_candidates", return_value=[])
@patch("app.services.lookup_stages.collect_smithsonian_scored_candidates", return_value=[])
@patch("app.services.lookup_stages.collect_aic_scored_candidates", return_value=[])
@patch("app.services.lookup_stages.collect_wikimedia_scored_candidates")
def test_lookup_stages_falls_back_to_wikimedia(
    mock_wikimedia: MagicMock,
    _mock_aic: MagicMock,
    _mock_si: MagicMock,
    _mock_nga: MagicMock,
    _mock_met: MagicMock,
) -> None:
    from app.sources.base import ArtworkLookupCandidate

    mock_wikimedia.return_value = [
        (
            0.62,
            {"title": "Example Portrait", "artist": "Example Artist"},
            ArtworkLookupCandidate(
                title="Example Portrait",
                artist="Example Artist",
                date=None,
                medium=None,
                image_url="https://upload.wikimedia.org/wikipedia/commons/1/1e/Example.jpg",
                image_thumbnail_url="https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Example.jpg/400px-Example.jpg",
                object_url="https://commons.wikimedia.org/wiki/File:Example.jpg",
                accession_number=None,
                source_name="Wikimedia Commons",
                confidence=0.62,
                rights_label="Wikimedia Commons",
                external_id="1",
            ),
        )
    ]

    result = lookup_artwork_candidates_staged(
        ArtworkLookupQuery(
            title="Example Portrait",
            artist="Example Artist",
            museum_name="The Met",
            has_title_query=True,
        ),
        allow_wikimedia_fallback=True,
    )

    assert result.candidates
    assert result.candidates[0].source_name == "Wikimedia Commons"
    mock_wikimedia.assert_called_once()
