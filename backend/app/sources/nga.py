"""National Gallery of Art open collection lookup (CC0 dataset)."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from app.sources.base import ArtworkLookupCandidate, ArtworkLookupQuery

NGA_SOURCE_NAME = "National Gallery of Art"
NGA_INDEX_PATH = Path(__file__).resolve().parent.parent / "data" / "nga_lookup_index.json"

NGA_MUSEUM_ALIASES = (
    "national gallery of art",
    "national gallery of art, washington",
    "nga",
)


def is_nga_museum(museum_name: str | None) -> bool:
    if not museum_name:
        return False
    normalized = _normalize(museum_name)
    return any(alias in normalized or normalized in alias for alias in NGA_MUSEUM_ALIASES)


def should_search_nga(query: ArtworkLookupQuery) -> bool:
    if query.source and query.source.strip().lower() in {"nga", "national gallery of art"}:
        return True
    return is_nga_museum(query.museum_name)


def search_nga_collection(
    query: ArtworkLookupQuery,
    *,
    limit: int = 8,
) -> list[ArtworkLookupCandidate]:
    if not should_search_nga(query):
        return []

    search_text, artist_text = _resolve_search_terms(query)
    if not search_text and not artist_text:
        return []

    scored: list[tuple[float, dict]] = []
    for entry in _load_index():
        score = _score_entry(entry, search_text, artist_text, query.year_period)
        if score >= 0.35:
            scored.append((score, entry))

    scored.sort(key=lambda item: item[0], reverse=True)
    results: list[ArtworkLookupCandidate] = []
    for score, entry in scored[:limit]:
        results.append(
            ArtworkLookupCandidate(
                title=entry["title"],
                artist=entry.get("artist"),
                date=entry.get("date"),
                medium=entry.get("medium"),
                image_url=entry.get("image_url"),
                image_thumbnail_url=entry.get("image_url"),
                object_url=entry.get("object_url"),
                accession_number=entry.get("accession_number"),
                source_name=NGA_SOURCE_NAME,
                confidence=round(min(score, 0.95), 2),
                rights_label=entry.get("rights_label"),
                external_id=entry.get("object_id"),
            )
        )
    return results


def _resolve_search_terms(query: ArtworkLookupQuery) -> tuple[str, str]:
    title = (query.title or "").strip()
    artist = (query.artist or "").strip()
    notes = (query.notes or "").strip()

    if title:
        return title, artist

    if notes:
        return notes, artist

    return "", artist


def _score_entry(
    entry: dict,
    search_text: str,
    artist_text: str,
    year_period: str | None,
) -> float:
    title = entry.get("title") or ""
    artist = entry.get("artist") or ""
    medium = entry.get("medium") or ""

    title_score = _text_similarity(search_text, title) if search_text else 0.0
    artist_score = _text_similarity(artist_text, artist) if artist_text else 0.0

    if search_text and title_score < 0.2:
        title_score = max(
            title_score,
            _token_overlap(search_text, f"{title} {medium}") * 0.85,
        )

    if not search_text and artist_text:
        title_score = max(title_score, _text_similarity(artist_text, title) * 0.5)

    if artist_text and artist_score < 0.25:
        return 0.0

    if search_text and artist_text:
        combined = title_score * 0.62 + artist_score * 0.38
    elif search_text:
        combined = title_score
    elif artist_text:
        combined = artist_score * 0.9
    else:
        combined = 0.0

    if year_period:
        combined += _year_bonus(year_period, entry.get("begin_year"), entry.get("end_year"))

    return min(combined, 1.0)


def _year_bonus(year_period: str, begin_year: str | None, end_year: str | None) -> float:
    years = [int(match) for match in re.findall(r"\d{3,4}", year_period)]
    if not years:
        return 0.0

    try:
        begin = int(begin_year) if begin_year else None
        end = int(end_year) if end_year else begin
    except ValueError:
        return 0.0

    if begin is None:
        return 0.0

    end = end or begin
    target = years[0]
    if begin <= target <= end:
        return 0.08
    if abs(target - begin) <= 25 or abs(target - end) <= 25:
        return 0.04
    return 0.0


def _text_similarity(left: str, right: str) -> float:
    left_norm = _normalize(left)
    right_norm = _normalize(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0
    if left_norm in right_norm or right_norm in left_norm:
        return 0.88
    return _token_overlap(left_norm, right_norm)


def _token_overlap(left: str, right: str) -> float:
    left_tokens = {token for token in _normalize(left).split() if len(token) > 2}
    right_tokens = {token for token in _normalize(right).split() if len(token) > 2}
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = left_tokens & right_tokens
    return len(intersection) / max(len(left_tokens), len(right_tokens))


def _normalize(value: str) -> str:
    lowered = value.lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return re.sub(r"\s+", " ", cleaned).strip()


@lru_cache(maxsize=1)
def _load_index() -> tuple[dict, ...]:
    if not NGA_INDEX_PATH.is_file():
        return ()
    with NGA_INDEX_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        return ()
    return tuple(item for item in data if isinstance(item, dict))
