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
    "emperor": frozenset({"emperor", "empereur"}),
    "napoleon": frozenset({"napoleon", "bonaparte"}),
}

TITLE_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "in",
        "at",
        "on",
        "of",
        "for",
        "to",
        "with",
        "from",
        "by",
        "as",
        "his",
        "her",
        "their",
        "its",
        "this",
        "that",
        "into",
        "during",
        "after",
        "before",
        "while",
    }
)

ATTRIBUTION_PREFIXES = (
    "circle of",
    "follower of",
    "school of",
    "after",
    "attributed to",
    "workshop of",
    "studio of",
    "manner of",
    "style of",
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


def meaningful_title_tokens(text: str) -> set[str]:
    return {token for token in expanded_tokens(text) if token not in TITLE_STOPWORDS}


def strip_leading_articles(text: str) -> str:
    tokens = normalize(text).split()
    while tokens and tokens[0] in {"the", "a", "an"}:
        tokens = tokens[1:]
    return " ".join(tokens)


def meaningful_title_overlap(left: str, right: str) -> float:
    left_tokens = meaningful_title_tokens(left)
    right_tokens = meaningful_title_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = left_tokens & right_tokens
    if not intersection:
        return 0.0
    return len(intersection) / max(len(left_tokens), len(right_tokens))


def strip_attribution_prefix(artist: str) -> str:
    normalized = normalize(artist)
    for prefix in ATTRIBUTION_PREFIXES:
        if normalized.startswith(prefix + " "):
            return normalized[len(prefix) + 1 :].strip()
    return normalized


def is_attribution_artist(artist: str) -> bool:
    normalized = normalize(artist)
    return any(normalized.startswith(prefix + " ") for prefix in ATTRIBUTION_PREFIXES)


def _artist_name_part(raw: str) -> str:
    text = raw.strip()
    for prefix in ATTRIBUTION_PREFIXES:
        if text.lower().startswith(prefix + " "):
            text = text[len(prefix) + 1 :].strip()

    if "," not in text:
        return text

    left, _, right = text.partition(",")
    right_lower = right.lower()
    if any(marker in right_lower for marker in ("born", "died", "active", "circa", "fl.", "c.")):
        return left.strip()

    left_words = [word for word in left.split() if word.strip()]
    right_words = [word for word in right.split() if word.strip()]
    if len(left_words) == 1 and len(right_words) <= 2:
        return left.strip()
    if len(left_words) <= 2 and len(right_words) <= 2:
        return left.strip()
    return text


def artist_name_surnames(artist: str) -> set[str]:
    name_part = _artist_name_part(artist)
    cleaned = normalize(name_part)
    if not cleaned:
        return set()

    words = [word for word in cleaned.split() if len(word) > 1]
    if not words:
        return set()
    if len(words) == 1:
        return {words[0]}
    return {words[-1]}


def artists_share_surname(left: str, right: str) -> bool:
    left_surnames = artist_name_surnames(left)
    right_surnames = artist_name_surnames(right)
    if not left_surnames or not right_surnames:
        return False
    return bool(left_surnames & right_surnames)


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

    search_core = strip_leading_articles(search_text)
    title_core = strip_leading_articles(title)

    direct = text_similarity(search_core, title_core)
    with_medium = text_similarity(search_core, f"{title_core} {medium}") if medium else 0.0
    fuzzy = fuzzy_ratio(search_core, title_core)
    meaningful = meaningful_title_overlap(search_text, title)

    phrase_bonus = 0.0
    search_tokens = meaningful_title_tokens(search_text)
    title_tokens = meaningful_title_tokens(title)
    if search_tokens and title_tokens and (search_tokens & title_tokens):
        phrase_bonus = min(0.35, 0.14 * len(search_tokens & title_tokens))

    return min(max(direct, with_medium, fuzzy, meaningful, phrase_bonus), 1.0)


def artist_similarity(artist_text: str, artist: str) -> float:
    if not artist_text or not artist:
        return 0.0

    query_core = strip_attribution_prefix(artist_text)
    entry_core = strip_attribution_prefix(artist)
    direct = text_similarity(query_core, entry_core)
    fuzzy = fuzzy_ratio(query_core, entry_core)

    query_surnames = artist_name_surnames(artist_text)
    entry_surnames = artist_name_surnames(artist)
    surname_match = bool(query_surnames & entry_surnames)

    if query_surnames and entry_surnames and not surname_match:
        shared_tokens = expanded_tokens(query_core) & expanded_tokens(entry_core)
        if shared_tokens:
            return min(max(direct, fuzzy), 0.18)
        return min(max(direct, fuzzy), 0.12)

    if surname_match:
        score = max(direct, fuzzy, 0.78)
        if is_attribution_artist(artist):
            return min(score, 0.58)
        return min(score, 0.98)

    query_parts = [part.strip() for part in re.split(r"[,;]", query_core) if part.strip()]
    entry_parts = [part.strip() for part in re.split(r"[,;]", entry_core) if part.strip()]
    if len(query_parts) >= 2 and len(entry_parts) >= 2:
        if normalize(query_parts[0]) == normalize(entry_parts[0]):
            return max(direct, 0.82)

    if direct >= 0.72 or fuzzy >= 0.82:
        if is_attribution_artist(artist):
            return min(max(direct, fuzzy), 0.58)
        return min(max(direct, fuzzy), 0.98)

    if is_attribution_artist(artist):
        return min(max(direct, fuzzy), 0.52)

    return min(max(direct, fuzzy), 0.28)


def passes_title_specific_gate(
    *,
    search_text: str,
    artist_text: str,
    entry: dict,
    title_score: float,
    artist_score: float,
    title_key: str = "title",
    artist_key: str = "artist",
) -> bool:
    title = entry.get(title_key) or ""
    artist = entry.get(artist_key) or ""
    meaningful = meaningful_title_overlap(search_text, title)
    normalized_title_match = fuzzy_ratio(
        strip_leading_articles(search_text),
        strip_leading_articles(title),
    )

    if meaningful >= 0.22:
        return True
    if normalized_title_match >= 0.82:
        return True
    if title_score >= 0.68:
        return True
    if artist_text and artist_score >= 0.78 and title_score >= 0.3:
        return True

    if artist_text and not is_placeholder_artist(artist_text) and artist:
        if not artists_share_surname(artist_text, artist) and artist_score < 0.72:
            return False

    return title_score >= 0.55 and artist_score >= 0.55


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

    if strict_artist_gate and artist_text and artist_score < 0.45:
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
