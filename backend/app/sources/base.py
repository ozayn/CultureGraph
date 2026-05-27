from dataclasses import dataclass


@dataclass(frozen=True)
class ArtworkLookupQuery:
    title: str | None
    artist: str | None
    museum_name: str | None
    year_period: str | None = None
    notes: str | None = None
    source: str | None = None
    has_title_query: bool = False
    expected_medium_type: str = "unknown"
    medium_type_filter: str = "any"
    medium_hint: str | None = None


@dataclass(frozen=True)
class ArtworkLookupCandidate:
    title: str
    artist: str | None
    date: str | None
    medium: str | None
    image_url: str | None
    object_url: str | None
    accession_number: str | None
    source_name: str
    confidence: float
    rights_label: str | None
    external_id: str | None = None
    image_thumbnail_url: str | None = None
    low_confidence: bool = False
    medium_type: str | None = None
    medium_match: bool | None = None
    match_reasons: tuple[str, ...] = ()
