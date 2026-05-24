import re
from dataclasses import dataclass, field


@dataclass
class ParsedArtworkFields:
    title: str | None = None
    artist: str | None = None
    period_or_year: str | None = None
    medium: str | None = None
    display_label: str | None = None
    concept_heading: str | None = None
    descriptive_label: str | None = None


def _clean_fragment(value: str) -> str:
    cleaned = value.strip().strip(".,;:")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _normalize_artist(value: str) -> str:
    artist = _clean_fragment(value)
    artist = re.sub(r"\s+'s$", "", artist, flags=re.IGNORECASE)
    return artist


def _descriptive_label_from_notes(block: str, artist: str | None) -> str | None:
    match = re.match(r"^(.+?)\s*[—–-]\s+(.+)$", block.strip())
    if match:
        left = _clean_fragment(match.group(1))
        right = _clean_fragment(match.group(2))
        if artist and left.lower() == artist.lower():
            return right[:80] if len(right) > 80 else right
    return None


def _finalize_display_label(
    fields: ParsedArtworkFields,
    block: str,
) -> ParsedArtworkFields:
    if fields.title:
        fields.display_label = fields.title
        return fields

    descriptive = fields.descriptive_label or _descriptive_label_from_notes(block, fields.artist)
    if fields.artist:
        fields.display_label = fields.artist
    elif descriptive:
        fields.display_label = descriptive
    elif fields.concept_heading:
        fields.display_label = fields.concept_heading
    else:
        fields.display_label = None

    return fields


def parse_artwork_fields(block: str) -> ParsedArtworkFields:
    text = block.strip()
    fields = ParsedArtworkFields()

    centers_on = re.search(
        r"centers on\s+(.+?)['']s\s+(.+?)(?:[.\-,;]|$)",
        text,
        re.IGNORECASE,
    )
    if centers_on:
        fields.artist = _normalize_artist(centers_on.group(1))
        fields.title = _clean_fragment(centers_on.group(2))
        return _finalize_display_label(fields, text)

    is_title_year_by = re.search(
        r"\bis\s+(.+?)\s*\((\d{4})\)\s+by\s+(.+?)(?:[.\-,;]|$)",
        text,
        re.IGNORECASE,
    )
    if is_title_year_by:
        fields.title = _clean_fragment(is_title_year_by.group(1))
        fields.period_or_year = is_title_year_by.group(2)
        fields.artist = _normalize_artist(is_title_year_by.group(3))
        return _finalize_display_label(fields, text)

    title_year_by = re.search(
        r"^(.+?)\s*\((\d{4})\)\s+by\s+(.+?)(?:[.\-,;]|$)",
        text,
        re.IGNORECASE,
    )
    if title_year_by:
        fields.title = _clean_fragment(title_year_by.group(1))
        fields.period_or_year = title_year_by.group(2)
        fields.artist = _normalize_artist(title_year_by.group(3))
        return _finalize_display_label(fields, text)

    medium_by = re.search(
        r"this is (?:a|an)\s+(.+?)\s+by\s+(.+?)(?:[.\-,;]|$)",
        text,
        re.IGNORECASE,
    )
    if medium_by:
        fields.medium = _clean_fragment(medium_by.group(1))
        fields.artist = _normalize_artist(medium_by.group(2))
        return _finalize_display_label(fields, text)

    title_by = re.search(
        r"(?:^|[,:]\s|\bis\s+)([A-Z][^(\n]+?)\s+by\s+([A-Za-z .']+?)(?:[.\-,;]|$)",
        text,
    )
    if title_by:
        candidate_title = _clean_fragment(title_by.group(1))
        if candidate_title.lower() not in {"this", "the mural", "the mural behind the sculpture"}:
            fields.title = candidate_title
            fields.artist = _normalize_artist(title_by.group(2))
            return _finalize_display_label(fields, text)

    is_by = re.search(
        r"this .+? is\s+by\s+(.+?)(?:[.\-,;]|$)",
        text,
        re.IGNORECASE,
    )
    if is_by:
        fields.artist = _normalize_artist(is_by.group(1))
        medium_match = re.search(
            r"this (?:wall-sized\s+)?(.+?)\s+is\s+by\s",
            text,
            re.IGNORECASE,
        )
        if medium_match:
            fields.medium = _clean_fragment(medium_match.group(1))
        return _finalize_display_label(fields, text)

    artist_and_concept = re.match(
        r"^([A-Za-z .']+?)\s+and\s+(.+?)(?:\s*[—–-]\s+(.+))?$",
        text,
        re.IGNORECASE,
    )
    if artist_and_concept:
        fields.artist = _normalize_artist(artist_and_concept.group(1))
        fields.concept_heading = _clean_fragment(artist_and_concept.group(2))
        if artist_and_concept.group(3):
            fields.descriptive_label = _clean_fragment(artist_and_concept.group(3))
        return _finalize_display_label(fields, text)

    artist_emdash = re.match(r"^([A-Za-z .']+?)\s*[—–-]\s+(.+)$", text)
    if artist_emdash:
        fields.artist = _normalize_artist(artist_emdash.group(1))
        fields.descriptive_label = _clean_fragment(artist_emdash.group(2))
        return _finalize_display_label(fields, text)

    by_only = re.search(r"\bby\s+([A-Za-z .']+?)(?:[.\-,;]|$)", text, re.IGNORECASE)
    if by_only:
        fields.artist = _normalize_artist(by_only.group(1))
        return _finalize_display_label(fields, text)

    return _finalize_display_label(fields, text)
