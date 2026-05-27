"""Separate identity certainty from visual similarity for collection matches."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.services.visual_analysis import extract_artist_from_ocr, extract_title_from_ocr
from app.sources.matching import normalize

MatchTier = Literal["high", "possible", "weak"]

VERIFIED_IDENTITY_MIN = 0.95
STRONG_IDENTITY_MIN = 0.80
POSSIBLE_IDENTITY_MIN = 0.60

GENERIC_PORTRAIT_TOKENS = frozenset(
    {
        "portrait",
        "figure",
        "figures",
        "bust",
        "head",
        "likeness",
        "study",
        "man",
        "woman",
        "male",
        "female",
        "gentleman",
        "lady",
        "seated",
        "standing",
        "unknown",
        "untitled",
    }
)

GENERIC_TITLE_TOKENS = frozenset(
    {
        "figure",
        "portrait",
        "study",
        "head",
        "bust",
        "man",
        "woman",
        "likeness",
        "subject",
        "unknown",
        "untitled",
    }
)


@dataclass(frozen=True)
class IdentityEvidence:
    exact_title_match: bool = False
    ocr_supported: bool = False
    artist_aligned: bool = False
    clip_similarity: float | None = None
    reverse_image_similarity: float | None = None
    museum_context_match: bool = False
    composition_overlap: bool = False
    subject_overlap: bool = False


@dataclass(frozen=True)
class CalibratedConfidence:
    identity_certainty: float
    visual_similarity: float
    confidence: float
    match_tier: MatchTier
    low_confidence: bool
    match_explanation: str
    match_reasons: tuple[str, ...]
    evidence: IdentityEvidence


def _token_set(text: str) -> set[str]:
    return {token for token in normalize(text).split() if len(token) > 2}


def is_generic_portrait_title(title: str) -> bool:
    tokens = _token_set(title)
    if not tokens:
        return True
    non_generic = tokens - GENERIC_TITLE_TOKENS - {
        "the",
        "and",
        "with",
        "from",
        "in",
        "on",
        "of",
        "a",
        "an",
    }
    if len(non_generic) >= 2:
        return False
    if tokens <= GENERIC_TITLE_TOKENS:
        return True
    return len(non_generic) <= 1 and bool(tokens.intersection(GENERIC_PORTRAIT_TOKENS))


def is_ambiguous_portrait_context(
    *,
    candidate_title: str,
    search_title: str,
    visual_subject: str | None,
) -> bool:
    haystack = " ".join(filter(None, [candidate_title, search_title, visual_subject])).lower()
    if not any(token in haystack for token in GENERIC_PORTRAIT_TOKENS):
        return False
    return is_generic_portrait_title(candidate_title) or is_generic_portrait_title(search_title)


def _ocr_supports_candidate(
    *,
    ocr_label_text: str | None,
    candidate_title: str,
    candidate_artist: str | None,
    title_score: float,
    artist_score: float,
) -> bool:
    if not ocr_label_text:
        return False

    ocr_title = extract_title_from_ocr(ocr_label_text)
    ocr_artist = extract_artist_from_ocr(ocr_label_text)
    title_ok = False
    if ocr_title:
        normalized_ocr = normalize(ocr_title)
        normalized_candidate = normalize(candidate_title)
        title_ok = (
            normalized_ocr == normalized_candidate
            or normalized_ocr in normalized_candidate
            or normalized_candidate in normalized_ocr
            or title_score >= 0.88
        )
    artist_ok = not ocr_artist or artist_score >= 0.72
    return title_ok and artist_ok


def _composition_overlap(visual_keywords: list[str] | None, candidate_title: str) -> bool:
    if not visual_keywords:
        return False
    title_tokens = _token_set(candidate_title)
    keyword_tokens: set[str] = set()
    for keyword in visual_keywords:
        keyword_tokens.update(_token_set(keyword))
    overlap = title_tokens & keyword_tokens
    return len(overlap) >= 2


def identity_tier(identity_certainty: float, *, verified: bool) -> MatchTier:
    if identity_certainty >= VERIFIED_IDENTITY_MIN and verified:
        return "high"
    if identity_certainty >= STRONG_IDENTITY_MIN:
        return "possible"
    if identity_certainty >= POSSIBLE_IDENTITY_MIN:
        return "possible"
    return "weak"


def build_match_explanation(
    *,
    identity_certainty: float,
    visual_similarity: float,
    evidence: IdentityEvidence,
    ambiguous_portrait: bool,
    matched_signals: list[str],
    missing_signals: list[str],
) -> str:
    if evidence.exact_title_match and evidence.artist_aligned:
        return "Exact title and artist alignment support this collection record."

    if evidence.ocr_supported:
        return "Wall-label OCR supports this catalog match."

    parts: list[str] = []
    if matched_signals:
        parts.append(f"Matched because: {', '.join(matched_signals)}.")
    else:
        parts.append("Matched mainly on broad visual or stylistic resemblance.")

    if missing_signals:
        parts.append(f"Not enough evidence for exact identification: {', '.join(missing_signals)}.")
    elif ambiguous_portrait:
        parts.append("Generic portrait titles are ambiguous without label OCR or exact title confirmation.")

    if visual_similarity >= 0.45 and identity_certainty < STRONG_IDENTITY_MIN:
        parts.append("Treat as visually similar, not a confirmed identity match.")

    return " ".join(parts)


def calibrate_candidate_confidence(
    *,
    title_score: float,
    artist_score: float,
    text_score: float,
    candidate_title: str,
    candidate_artist: str | None,
    search_title: str,
    search_artist: str,
    has_title_query: bool,
    match_reasons: list[str],
    ocr_label_text: str | None = None,
    visual_subject: str | None = None,
    visual_keywords: list[str] | None = None,
    visual_overlap: float = 0.0,
    subject_overlap: float = 0.0,
    medium_mismatch: bool = False,
    attribution: bool = False,
    clip_similarity: float | None = None,
    reverse_image_similarity: float | None = None,
    museum_context_match: bool = False,
) -> CalibratedConfidence:
    exact_title_match = has_title_query and title_score >= 0.92
    artist_aligned = bool(search_artist.strip()) and artist_score >= 0.78
    ocr_supported = _ocr_supports_candidate(
        ocr_label_text=ocr_label_text,
        candidate_title=candidate_title,
        candidate_artist=candidate_artist,
        title_score=title_score,
        artist_score=artist_score,
    )
    composition_overlap = _composition_overlap(visual_keywords, candidate_title)
    subject_overlap_flag = subject_overlap >= 0.25

    evidence = IdentityEvidence(
        exact_title_match=exact_title_match,
        ocr_supported=ocr_supported,
        artist_aligned=artist_aligned,
        clip_similarity=clip_similarity,
        reverse_image_similarity=reverse_image_similarity,
        museum_context_match=museum_context_match,
        composition_overlap=composition_overlap,
        subject_overlap=subject_overlap_flag,
    )

    verified_by_image = (
        (clip_similarity is not None and clip_similarity >= 0.95)
        or (reverse_image_similarity is not None and reverse_image_similarity >= 0.95)
    )
    verified = exact_title_match or ocr_supported or verified_by_image

    if has_title_query and search_title.strip():
        identity = title_score * 0.62 + artist_score * 0.38
    elif search_artist.strip():
        identity = artist_score * 0.72 + title_score * 0.28
    else:
        identity = min(text_score * 0.45, 0.50)

    if exact_title_match and artist_aligned:
        identity = max(identity, 0.96)
    elif exact_title_match:
        identity = max(identity, 0.88)
    elif ocr_supported:
        identity = max(identity, 0.96)
    elif verified_by_image:
        identity = max(identity, 0.95)

    if has_title_query and search_title.strip() and title_score < 0.35:
        identity = min(identity * 0.35, 0.42)
    if search_artist.strip() and artist_score < 0.35:
        identity = min(identity * 0.30, 0.38)

    if medium_mismatch:
        identity = min(identity * 0.75, identity)

    if attribution:
        identity = min(identity, 0.58)

    ambiguous_portrait = is_ambiguous_portrait_context(
        candidate_title=candidate_title,
        search_title=search_title,
        visual_subject=visual_subject,
    )
    if ambiguous_portrait and not verified:
        identity = min(identity, 0.55)
        if title_score < 0.45 and artist_score < 0.55:
            identity = min(identity, 0.48)

    if is_generic_portrait_title(candidate_title) and not verified:
        identity = min(identity, 0.52)

    if identity >= VERIFIED_IDENTITY_MIN and not verified:
        identity = min(identity, 0.94)

    visual_similarity = min(
        visual_overlap * 0.55 + subject_overlap * 0.30 + (0.15 if composition_overlap else 0.0),
        1.0,
    )
    if not visual_keywords and not visual_subject:
        visual_similarity = min(visual_similarity, max(title_score * 0.35, 0.15))

    identity = round(max(0.0, min(identity, 1.0)), 2)
    visual_similarity = round(max(0.0, min(visual_similarity, 1.0)), 2)

    tier = identity_tier(identity, verified=verified)
    if ambiguous_portrait and not verified and tier == "high":
        tier = "possible"

    matched_signals = list(match_reasons[:3])
    if subject_overlap_flag:
        matched_signals.append("subject description overlap")
    if composition_overlap:
        matched_signals.append("composition overlap")

    missing_signals: list[str] = []
    if has_title_query and title_score < 0.55:
        missing_signals.append("exact title confirmation")
    if search_artist.strip() and artist_score < 0.65:
        missing_signals.append("artist confirmation")
    if ambiguous_portrait and not ocr_supported:
        missing_signals.append("unique portrait identity markers")
    if not composition_overlap and ambiguous_portrait:
        missing_signals.append("distinct composition overlap")

    explanation = build_match_explanation(
        identity_certainty=identity,
        visual_similarity=visual_similarity,
        evidence=evidence,
        ambiguous_portrait=ambiguous_portrait,
        matched_signals=matched_signals,
        missing_signals=missing_signals,
    )

    low_confidence = tier == "weak" or medium_mismatch or (
        ambiguous_portrait and not verified and identity < STRONG_IDENTITY_MIN
    )

    return CalibratedConfidence(
        identity_certainty=identity,
        visual_similarity=visual_similarity,
        confidence=identity,
        match_tier=tier,
        low_confidence=low_confidence,
        match_explanation=explanation,
        match_reasons=tuple(match_reasons[:4]),
        evidence=evidence,
    )
