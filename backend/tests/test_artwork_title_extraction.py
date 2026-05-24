import pytest

from app.services.artwork_note_parser import parse_artwork_fields
from app.services.museum_notes_import import MockMuseumNotesImportProvider
from app.schemas import MuseumNotesImportRequest


@pytest.mark.parametrize(
    ("note", "title", "artist", "year", "medium"),
    [
        (
            "Grandma Moses — nighttime baseball scene, small-town lights",
            None,
            "Grandma Moses",
            None,
            None,
        ),
        (
            "The mural behind the sculpture is Brooklyn Waterfront (2014) by Sanford Biggers",
            "Brooklyn Waterfront",
            "Sanford Biggers",
            "2014",
            None,
        ),
        (
            "This installation centers on Sanford Biggers's Reclining Liberty",
            "Reclining Liberty",
            "Sanford Biggers",
            None,
            None,
        ),
        (
            "Manifest Destiny (2004) by Alexis Rockman",
            "Manifest Destiny",
            "Alexis Rockman",
            "2004",
            None,
        ),
        (
            "This is a drape painting by Sam Gilliam",
            None,
            "Sam Gilliam",
            None,
            "drape painting",
        ),
    ],
)
@pytest.mark.asyncio
async def test_artwork_title_extraction_examples(
    note: str,
    title: str | None,
    artist: str,
    year: str | None,
    medium: str | None,
) -> None:
    parsed = parse_artwork_fields(note)
    assert parsed.title == title
    assert parsed.artist == artist
    assert parsed.period_or_year == year
    assert parsed.medium == medium

    provider = MockMuseumNotesImportProvider()
    result = await provider.extract(
        MuseumNotesImportRequest(text=note, default_museum="Test Museum", default_city="DC")
    )
    artwork = result.artworks[0]
    assert artwork.title == title
    assert artwork.artist == artist
    assert artwork.period_or_year == year
    assert artwork.medium == medium


@pytest.mark.asyncio
async def test_grandma_moses_has_null_title_and_artist_display_label() -> None:
    note = "Grandma Moses — nighttime baseball scene, small-town lights"
    parsed = parse_artwork_fields(note)
    assert parsed.title is None
    assert parsed.artist == "Grandma Moses"
    assert parsed.display_label == "Grandma Moses"


@pytest.mark.asyncio
async def test_sam_gilliam_has_artist_but_null_title() -> None:
    note = "This is a drape painting by Sam Gilliam"
    parsed = parse_artwork_fields(note)
    assert parsed.title is None
    assert parsed.artist == "Sam Gilliam"
    assert parsed.medium == "drape painting"
    assert parsed.display_label == "Sam Gilliam"
