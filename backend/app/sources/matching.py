"""Shared text/date scoring for museum collection lookup adapters."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

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

TOKEN_SYNONYMS: dict[str, frozenset[str]] = {
    "dancer": frozenset({"dancer", "dancers", "ballet", "dancing", "dance"}),
    "dancers": frozenset({"dancer", "dancers", "ballet", "dancing", "dance"}),
    "ballet": frozenset({"ballet", "dancer", "dancers", "dancing"}),
    "rehearsal": frozenset({"rehearsal", "rehearsing", "rehearse", "practice"}),
    "rehearsing": frozenset({"rehearsal", "rehearsing", "rehearse"}),
    "blue": frozenset({"blue", "bleu"}),
    "woman": frozenset({"woman", "women", "female", "femme"}),
    "women": frozenset({"woman", "women", "female", "femme"}),
}


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


def expanded_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for token in normalize(text).split():
        if len(token) <= 2:
            continue
        tokens.add(token)
        if token.endswith("s") and len(token) > 3:
            tokens.add(token[:-1])
        tokens.update(TOKEN_SYNONYMS.get(token, frozenset()))
    return tokens


def fuzzy_ratio(left: str, right: str) -> float:
    left_norm = normalize(left)
    right_norm = normalize(right)
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def token_overlap(left: str, right: str) -> float:
    left_tokens = expanded_tokens(left)
    right_tokens = expanded_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = left_tokens & right_tokens
    return len(intersection) / max(len(left_tokens), len(right_tokens))


def text_similarity(left: str, right: str) -> float:
    left_norm = normalize(left)
    right_norm = normalize(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0
    if left_norm in right_norm or right_norm in left_norm:
        return 0.88
    return max(token_overlap(left_norm, right_norm), fuzzy_ratio(left_norm, right_norm) * 0.92)


def title_similarity(search_text: str, title: str, medium: str = "") -> float:
    if not search_text:
        return 0.0

    direct = text_similarity(search_text, title)
    with_medium = text_similarity(search_text, f"{title} {medium}") if medium else 0.0
    fuzzy = fuzzy_ratio(search_text, title)

    phrase_bonus = 0.0
    search_tokens = expanded_tokens(search_text)
    title_tokens = expanded_tokens(title)
    if search_tokens and title_tokens and (search_tokens & title_tokens):
        phrase_bonus = min(0.35, 0.12 * len(search_tokens & title_tokens))

    return min(max(direct, with_medium, fuzzy, phrase_bonus), 1.0)


def artist_similarity(artist_text: str, artist: str) -> float:
    if not artist_text or not artist:
        return 0.0

    direct = text_similarity(artist_text, artist)
    if direct >= 0.72:
        return direct

    query_tokens = expanded_tokens(artist_text)
    entry_tokens = expanded_tokens(artist)
    if query_tokens & entry_tokens:
        overlap = len(query_tokens & entry_tokens) / max(len(query_tokens), len(entry_tokens))
        return max(direct, min(0.95, 0.55 + overlap * 0.4))

    query_parts = [part.strip() for part in re.split(r"[,;]", artist_text) if part.strip()]
    entry_parts = [part.strip() for part in re.split(r"[,;]", artist) if part.strip()]
    query_surnames = {normalize(part) for part in query_parts if part}
    entry_surnames = {normalize(part) for part in entry_parts if part}
    if query_surnames & entry_surnames:
        return max(direct, 0.78)

    return direct


def score_artwork_entry_detailed(
    entry: dict,
    search_text: str,
    artist_text: str,
    year_period: str | None,
    *,
    title_key: str = "title",
    artist_key: str = "artist",
    medium_key: str = "medium",
    strict_artist_gate: bool = True,
) -> ScoreDetails:
    title = entry.get(title_key) or ""
    artist = entry.get(artist_key) or ""
    medium = entry.get(medium_key) or ""

    title_score = title_similarity(search_text, title, medium) if search_text else 0.0
    artist_score = artist_similarity(artist_text, artist) if artist_text else 0.0

    if not search_text and artist_text:
        title_score = max(title_score, text_similarity(artist_text, title) * 0.45)

    if strict_artist_gate and artist_text and artist_score < 0.35:
        return ScoreDetails(combined=0.0, title_score=title_score, artist_score=artist_score)

    if search_text and artist_text:
        combined = title_score * 0.62 + artist_score * 0.38
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
    strict_artist_gate: bool = True,
) -> float:
    return score_artwork_entry_detailed(
        entry,
        search_text,
        artist_text,
        year_period,
        title_key=title_key,
        artist_key=artist_key,
        medium_key=medium_key,
        strict_artist_gate=strict_artist_gate,
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


def normalize(value: str) -> str:
    lowered = value.lower()
    cleaned = re.sub(r"[^a-z0-9\s]", " ", lowered)
    return re.sub(r"\s+", " ", cleaned).strip()
