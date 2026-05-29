"""Semantic artwork search: title normalization, query expansion, multi-phrase scoring."""

from __future__ import annotations

import re
from typing import Iterable

from app.sources.matching import (
    artist_similarity,
    expanded_tokens,
    meaningful_title_tokens,
    normalize,
    strip_leading_articles,
    text_similarity,
    title_similarity,
    token_overlap,
)

TITLE_PREFIX_PATTERNS = (
    r"^study for\s+",
    r"^studies for\s+",
    r"^sketch for\s+",
    r"^after\s+",
    r"^copy after\s+",
    r"^attributed to\s+",
    r"^circle of\s+",
    r"^manner of\s+",
)

NUMBER_WORDS = {
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
}

SUBJECT_EXPANSIONS: dict[str, tuple[str, ...]] = {
    "four dancers": (
        "dancers",
        "ballet dancers",
        "four figures",
        "ballet rehearsal",
        "pastel dancers",
        "dance scene",
    ),
    "dancers": (
        "ballet dancers",
        "dance scene",
        "ballet rehearsal",
        "figures dancing",
    ),
    "dancer": (
        "dancers",
        "ballet",
        "dance",
        "ballet dancer",
    ),
    "bathers": (
        "bathing figures",
        "bather",
        "bath scene",
    ),
    "bather": (
        "bathers",
        "bathing figures",
    ),
}

ARTIST_EXPANSIONS: dict[str, tuple[str, ...]] = {
    "degas": ("degas dancers", "degas ballet", "degas pastel"),
    "cezanne": ("cezanne landscape", "cezanne bather"),
}


def normalize_catalog_title(title: str | None) -> str:
    """Normalize catalog titles for semantic comparison."""
    if not title:
        return ""

    text = normalize(title)
    if not text or text in {"untitled", "unknown", "without title"}:
        return ""

    for pattern in TITLE_PREFIX_PATTERNS:
        text = re.sub(pattern, "", text)

    text = re.sub(r"\bno\.?\s*\d+\b", " ", text)
    text = re.sub(r"\b\d+\s*(st|nd|rd|th)\b", " ", text)
    text = re.sub(r"\(\s*\d+\s*\)", " ", text)
    text = re.sub(r"\bversion\s+\d+\b", " ", text)

    tokens: list[str] = []
    for token in text.split():
        if token in NUMBER_WORDS:
            tokens.append(NUMBER_WORDS[token])
        else:
            tokens.append(token)

    return strip_leading_articles(" ".join(dict.fromkeys(tokens)))


def semantic_title_similarity(search_text: str, candidate_title: str, *, medium: str = "") -> float:
    """Compare titles using normalization plus token/fuzzy overlap — not exact equality."""
    if not search_text or not candidate_title:
        return 0.0

    search_norm = normalize_catalog_title(search_text) or strip_leading_articles(search_text)
    title_norm = normalize_catalog_title(candidate_title) or strip_leading_articles(candidate_title)

    direct = text_similarity(search_norm, title_norm)
    fuzzy = token_overlap(search_norm, title_norm)
    legacy = title_similarity(search_text, candidate_title, medium)

    search_tokens = meaningful_title_tokens(search_norm)
    title_tokens = meaningful_title_tokens(title_norm)
    overlap = 0.0
    if search_tokens and title_tokens:
        overlap = len(search_tokens & title_tokens) / max(len(search_tokens), len(title_tokens))

    return min(max(direct, fuzzy, legacy, overlap), 1.0)


def expand_artwork_search_terms(
    *,
    title: str | None = None,
    artist: str | None = None,
    visual_keywords: Iterable[str] | None = None,
) -> list[str]:
    """Expand a hypothesized title/artist into museum-search phrases."""
    terms: list[str] = []
    title_clean = (title or "").strip()
    artist_clean = (artist or "").strip()

    if title_clean and not _is_placeholder(title_clean):
        terms.append(title_clean)
        normalized = normalize_catalog_title(title_clean)
        if normalized and normalized != normalize(title_clean):
            terms.append(normalized)

        title_key = normalize(title_clean)
        if title_key in SUBJECT_EXPANSIONS:
            terms.extend(SUBJECT_EXPANSIONS[title_key])

        title_tokens = meaningful_title_tokens(title_clean)
        if "dancers" in title_tokens or "dancer" in title_tokens:
            terms.extend(SUBJECT_EXPANSIONS["dancers"])
        if "four" in title_tokens and ("dancers" in title_tokens or "dancer" in title_tokens):
            terms.extend(SUBJECT_EXPANSIONS["four dancers"])

    if artist_clean and not _is_placeholder(artist_clean):
        terms.append(artist_clean)
        surname = artist_clean.split()[-1] if artist_clean.split() else artist_clean
        artist_key = normalize(surname)
        if artist_key in ARTIST_EXPANSIONS:
            terms.extend(ARTIST_EXPANSIONS[artist_key])
        if title_clean:
            terms.append(f"{artist_clean} {title_clean}")
            terms.append(f"{surname} {normalize_catalog_title(title_clean) or title_clean}")

    if visual_keywords:
        terms.extend(str(keyword).strip() for keyword in visual_keywords if str(keyword).strip())

    return _dedupe_preserve_order(terms)


def combined_search_phrases(
    *,
    title: str | None,
    artist: str | None,
    visual_keywords: Iterable[str] | None = None,
    notes: str | None = None,
) -> tuple[str, ...]:
    expanded = expand_artwork_search_terms(
        title=title,
        artist=artist,
        visual_keywords=visual_keywords,
    )
    if notes and notes.strip():
        expanded.append(notes.strip())
    return tuple(expanded)


def best_semantic_entry_score(
    entry: dict,
    search_phrases: tuple[str, ...],
    artist_text: str,
    year_period: str | None,
    *,
    title_key: str = "title",
    artist_key: str = "artist",
    medium_key: str = "medium",
) -> tuple[float, float, float]:
    """Return best (combined, title_score, artist_score) across semantic search phrases."""
    title = entry.get(title_key) or ""
    artist = entry.get(artist_key) or ""
    medium = entry.get(medium_key) or ""

    best_title = 0.0
    best_combined = 0.0
    artist_score = artist_similarity(artist_text, artist) if artist_text else 0.0

    phrases = search_phrases or ("",)
    for phrase in phrases:
        if not phrase.strip() and not artist_text:
            continue
        title_score = semantic_title_similarity(phrase, title, medium=medium) if phrase.strip() else 0.0
        if phrase.strip() and artist_text:
            combined = title_score * 0.52 + artist_score * 0.48
        elif phrase.strip():
            combined = title_score
        elif artist_text:
            combined = artist_score * 0.9
        else:
            combined = 0.0

        best_title = max(best_title, title_score)
        best_combined = max(best_combined, combined)

    if artist_text and not search_phrases:
        best_combined = max(best_combined, artist_score * 0.9)

    return min(best_combined, 1.0), best_title, artist_score


def _dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in values:
        cleaned = re.sub(r"\s+", " ", raw.strip())
        if not cleaned:
            continue
        key = normalize(cleaned)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(cleaned)
    return ordered


def _is_placeholder(value: str) -> bool:
    from app.sources.matching import is_placeholder_artist, is_placeholder_title

    return is_placeholder_title(value) or is_placeholder_artist(value)
