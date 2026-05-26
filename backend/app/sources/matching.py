"""Shared text/date scoring for museum collection lookup adapters."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.sources.base import ArtworkLookupQuery

PLACEHOLDER_TITLES = frozenset(
    {
        "unknown",
        "untitled",
        "unidentified artwork",
        "unidentified",
        "painting",
        "artwork",
        "work",
        "no title",
        "untitled artwork",
        "unknown artwork",
        "unknown title",
    }
)

PLACEHOLDER_ARTISTS = frozenset(
    {
        "unknown",
        "unknown artist",
        "unidentified",
        "anonymous",
        "attributed",
        "artist unknown",
    }
)


@dataclass(frozen=True)
class ScoreDetails:
    combined: float
    title_score: float
    artist_score: float


def is_placeholder_title(value: str | None) -> bool:
    cleaned = normalize(value or "")
    if not cleaned:
        return True
    return cleaned in PLACEHOLDER_TITLES


def is_placeholder_artist(value: str | None) -> bool:
    cleaned = normalize(value or "")
    if not cleaned:
        return True
    return cleaned in PLACEHOLDER_ARTISTS


def resolve_search_terms(query: ArtworkLookupQuery) -> tuple[str, str]:
    title = (query.title or "").strip()
    artist = (query.artist or "").strip()
    notes = (query.notes or "").strip()

    if title and not is_placeholder_title(title):
        return title, artist if not is_placeholder_artist(artist) else ""

    if notes:
        return notes, artist if not is_placeholder_artist(artist) else ""

    return "", artist if not is_placeholder_artist(artist) else ""


def score_artwork_entry_detailed(
    entry: dict,
    search_text: str,
    artist_text: str,
    year_period: str | None,
    *,
    title_key: str = "title",
    artist_key: str = "artist",
    medium_key: str = "medium",
) -> ScoreDetails:
    title = entry.get(title_key) or ""
    artist = entry.get(artist_key) or ""
    medium = entry.get(medium_key) or ""

    title_score = text_similarity(search_text, title) if search_text else 0.0
    artist_score = text_similarity(artist_text, artist) if artist_text else 0.0

    if search_text and title_score < 0.2:
        title_score = max(
            title_score,
            token_overlap(search_text, f"{title} {medium}") * 0.85,
        )

    if not search_text and artist_text:
        title_score = max(title_score, text_similarity(artist_text, title) * 0.5)

    if artist_text and artist_score < 0.25:
        return ScoreDetails(combined=0.0, title_score=title_score, artist_score=artist_score)

    if search_text and artist_text:
        combined = title_score * 0.68 + artist_score * 0.32
    elif search_text:
        combined = title_score
    elif artist_text:
        combined = artist_score * 0.9
    else:
        combined = 0.0

    if year_period:
        combined += year_bonus(year_period, entry.get("begin_year"), entry.get("end_year"))

    return ScoreDetails(
        combined=min(combined, 1.0),
        title_score=title_score,
        artist_score=artist_score,
    )


def score_artwork_entry(
    entry: dict,
    search_text: str,
    artist_text: str,
    year_period: str | None,
    *,
    title_key: str = "title",
    artist_key: str = "artist",
    medium_key: str = "medium",
) -> float:
    return score_artwork_entry_detailed(
        entry,
        search_text,
        artist_text,
        year_period,
        title_key=title_key,
        artist_key=artist_key,
        medium_key=medium_key,
    ).combined


def year_bonus(year_period: str, begin_year: str | None, end_year: str | None) -> float:
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


def text_similarity(left: str, right: str) -> float:
    left_norm = normalize(left)
    right_norm = normalize(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0
    if left_norm in right_norm or right_norm in left_norm:
        return 0.88
    return token_overlap(left_norm, right_norm)


def token_overlap(left: str, right: str) -> float:
    left_tokens = {token for token in normalize(left).split() if len(token) > 2}
    right_tokens = {token for token in normalize(right).split() if len(token) > 2}
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = left_tokens & right_tokens
    return len(intersection) / max(len(left_tokens), len(right_tokens))


def normalize(value: str) -> str:
    lowered = value.lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return re.sub(r"\s+", " ", cleaned).strip()
