"""Retrieval-assisted artwork identification — calibrate vision output with museum matches."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas import ArtworkLookupCandidateRead, ArtworkLookupResponse, ResearchDraft
from app.services.visual_analysis import (
    VisualAnalysis,
    build_visual_summary,
    collect_visual_keywords,
)
from app.sources.matching import normalize


def _token_set(text: str) -> set[str]:
    return {token for token in normalize(text).split() if len(token) > 2}

IdentificationMode = Literal["catalog_match", "possible_match", "style_subject"]
ConfidenceLevel = Literal["high", "medium", "low"]

HIGH_CONFIDENCE = 0.72
MEDIUM_CONFIDENCE = 0.55


class ArtworkIdentification(BaseModel):
    identification_mode: IdentificationMode
    confidence_level: ConfidenceLevel
    display_summary: str
    style_assessment: str | None = None
    subject_assessment: str | None = None
    iconography_notes: list[str] = Field(default_factory=list)
    top_candidate: ArtworkLookupCandidateRead | None = None
    alternative_matches: list[ArtworkLookupCandidateRead] = Field(default_factory=list)
    match_reasons: list[str] = Field(default_factory=list)
    suggested_title: str | None = None
    suggested_artist: str | None = None
    visual_keywords: list[str] = Field(default_factory=list)
    catalog_confidence: float | None = Field(default=None, ge=0.0, le=1.0)


def _visual_overlap_score(candidate: ArtworkLookupCandidateRead, keywords: list[str]) -> float:
    if not keywords:
        return 0.0
    haystack = normalize(
        " ".join(
            filter(
                None,
                [candidate.title, candidate.artist, candidate.medium, candidate.date],
            )
        )
    )
    if not haystack:
        return 0.0

    keyword_tokens: set[str] = set()
    for keyword in keywords:
        keyword_tokens.update(_token_set(keyword))

    if not keyword_tokens:
        return 0.0

    hay_tokens = _token_set(haystack)
    overlap = len(keyword_tokens & hay_tokens)
    return min(overlap / max(len(keyword_tokens), 1), 1.0)


def rerank_candidates_with_visual(
    candidates: list[ArtworkLookupCandidateRead],
    visual: VisualAnalysis | None,
    visual_keywords: list[str],
) -> list[ArtworkLookupCandidateRead]:
    if not candidates:
        return []

    boosted: list[tuple[float, ArtworkLookupCandidateRead]] = []
    for candidate in candidates:
        overlap = _visual_overlap_score(candidate, visual_keywords)
        subject_overlap = 0.0
        if visual and visual.subject:
            subject_overlap = _visual_overlap_score(candidate, [visual.subject])
        style_overlap = 0.0
        if visual and visual.style_signals:
            style_overlap = _visual_overlap_score(candidate, visual.style_signals[:4])

        visual_boost = overlap * 0.12 + subject_overlap * 0.08 + style_overlap * 0.05
        adjusted_confidence = min(candidate.confidence + visual_boost, 0.98)
        low_confidence = candidate.low_confidence
        if adjusted_confidence >= HIGH_CONFIDENCE and overlap >= 0.25:
            low_confidence = False
        elif adjusted_confidence < MEDIUM_CONFIDENCE:
            low_confidence = True

        reasons = list(candidate.match_reasons or [])
        if overlap >= 0.2:
            reasons.append("Visual keyword overlap")
        if subject_overlap >= 0.25:
            reasons.append("Subject description overlap")
        if style_overlap >= 0.2:
            reasons.append("Style signal overlap")

        boosted.append(
            (
                adjusted_confidence,
                candidate.model_copy(
                    update={
                        "confidence": round(adjusted_confidence, 2),
                        "low_confidence": low_confidence,
                        "match_reasons": reasons[:5],
                    }
                ),
            )
        )

    boosted.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in boosted]


def _confidence_level(score: float | None, *, low_flag: bool) -> ConfidenceLevel:
    if score is None or low_flag:
        return "low"
    if score >= HIGH_CONFIDENCE:
        return "high"
    if score >= MEDIUM_CONFIDENCE:
        return "medium"
    return "low"


def _style_assessment(visual: VisualAnalysis | None, period: str | None) -> str | None:
    if visual and visual.movement_style:
        return visual.movement_style
    if period:
        return period
    if visual and visual.period_clues:
        return ", ".join(visual.period_clues[:2])
    if visual and visual.style_signals:
        return f"Style resembles {', '.join(visual.style_signals[:2])}"
    return None


def _subject_assessment(visual: VisualAnalysis | None) -> str | None:
    if not visual:
        return None
    if visual.subject:
        return visual.subject
    parts = [*visual.clothing[:2], *visual.notable_objects[:2]]
    if parts:
        return ", ".join(parts)
    return None


def _iconography_notes(visual: VisualAnalysis | None) -> list[str]:
    if not visual:
        return []
    notes: list[str] = []
    if visual.notable_objects:
        notes.append(f"Notable objects: {', '.join(visual.notable_objects[:4])}")
    if visual.clothing:
        notes.append(f"Clothing / dress: {', '.join(visual.clothing[:3])}")
    if visual.composition:
        notes.append(f"Composition: {', '.join(visual.composition[:3])}")
    return notes[:3]


def _related_works_phrase(top: ArtworkLookupCandidateRead) -> str:
    artist = (top.artist or "").strip()
    if artist:
        return f"works associated with {artist}"
    return f"“{top.title}” and similar catalog entries"


def build_identification(
    draft: ResearchDraft,
    lookup: ArtworkLookupResponse,
    visual: VisualAnalysis | None = None,
) -> ArtworkIdentification:
    visual = visual or draft.visual_analysis
    keywords = collect_visual_keywords(
        visual,
        period_or_movement=draft.period_or_movement,
        ocr_label_text=draft.ocr_label_text,
    )

    reranked = rerank_candidates_with_visual(lookup.candidates, visual, keywords)
    top = reranked[0] if reranked else None
    alternatives = reranked[1:4] if len(reranked) > 1 else []

    style = _style_assessment(visual, draft.period_or_movement)
    subject = _subject_assessment(visual)
    iconography = _iconography_notes(visual)

    catalog_score = top.confidence if top else None
    low_flag = bool(top and top.low_confidence)
    level = _confidence_level(catalog_score, low_flag=low_flag)

    match_reasons: list[str] = list(top.match_reasons) if top else []
    if lookup.query_used:
        match_reasons.append(f"Searched collections for: {lookup.query_used}")

    if top and catalog_score is not None and catalog_score >= HIGH_CONFIDENCE and not low_flag:
        mode: IdentificationMode = "catalog_match"
        artist_suffix = f" by {top.artist}" if top.artist else ""
        display = f"Collection match: {top.title}{artist_suffix} ({top.source_name})."
        suggested_title = top.title
        suggested_artist = top.artist
    elif top and catalog_score is not None and catalog_score >= MEDIUM_CONFIDENCE:
        mode = "possible_match"
        artist_suffix = f" by {top.artist}" if top.artist else ""
        style_bit = style or "this period/style"
        display = (
            f"Possible match: {top.title}{artist_suffix}. "
            f"Also consider {style_bit} — verify against the image and catalog record."
        )
        suggested_title = None
        suggested_artist = None
        if not match_reasons:
            match_reasons.append("Moderate catalog similarity — not confirmed")
    elif top:
        mode = "possible_match"
        style_bit = style or "this period/style"
        subject_bit = subject or "the depicted subject"
        display = (
            f"Possibly {style_bit} depicting {subject_bit.rstrip('.')}. "
            f"Potentially related to {_related_works_phrase(top)} — review matches below."
        )
        suggested_title = None
        suggested_artist = None
        level = "low"
    else:
        mode = "style_subject"
        style_bit = style or "an unidentified work in this style"
        subject_bit = subject or "an unidentified subject"
        display = (
            f"Possibly {style_bit}. Subject: {subject_bit.rstrip('.')}. "
            "No strong catalog match — style and iconography notes below."
        )
        suggested_title = None
        suggested_artist = None
        level = "low"

    if mode == "style_subject" and visual and visual.style_signals:
        display += f" Style resembles {', '.join(visual.style_signals[:2])}."

    return ArtworkIdentification(
        identification_mode=mode,
        confidence_level=level,
        display_summary=display,
        style_assessment=style,
        subject_assessment=subject,
        iconography_notes=iconography,
        top_candidate=top,
        alternative_matches=alternatives,
        match_reasons=match_reasons[:6],
        suggested_title=suggested_title,
        suggested_artist=suggested_artist,
        visual_keywords=keywords[:12],
        catalog_confidence=catalog_score,
    )


def calibrate_research_draft(
    draft: ResearchDraft,
    identification: ArtworkIdentification,
    visual: VisualAnalysis | None = None,
) -> ResearchDraft:
    """Apply retrieval-assisted calibration — avoid hallucinated exact titles."""
    visual = visual or draft.visual_analysis
    updated = draft.model_copy(deep=True)
    updated.short_summary = identification.display_summary

    if identification.identification_mode == "catalog_match":
        if identification.suggested_title:
            updated.possible_title = identification.suggested_title
        if identification.suggested_artist:
            updated.possible_artist = identification.suggested_artist
        updated.confidence = identification.catalog_confidence or updated.confidence
    else:
        if draft.ocr_label_text:
            updated.possible_title = draft.possible_title
            updated.possible_artist = draft.possible_artist
        else:
            updated.possible_title = None
            updated.possible_artist = None
        if identification.catalog_confidence is not None:
            updated.confidence = min(
                identification.catalog_confidence,
                draft.confidence or identification.catalog_confidence,
            )
        elif visual:
            updated.confidence = min(draft.confidence or 0.45, 0.55)

    if not updated.short_summary:
        updated.short_summary = build_visual_summary(
            visual,
            period_or_movement=updated.period_or_movement,
            vision_confidence=updated.confidence or 0.4,
        )

    return updated


def lookup_with_identification_candidates(
    lookup: ArtworkLookupResponse,
    identification: ArtworkIdentification,
) -> ArtworkLookupResponse:
    """Return lookup response with visually reranked candidate ordering."""
    ordered: list[ArtworkLookupCandidateRead] = []
    seen: set[str] = set()

    def add(candidate: ArtworkLookupCandidateRead | None) -> None:
        if not candidate:
            return
        key = candidate.external_id or candidate.object_url or candidate.title
        if key in seen:
            return
        seen.add(key)
        ordered.append(candidate)

    add(identification.top_candidate)
    for candidate in identification.alternative_matches:
        add(candidate)
    for candidate in lookup.candidates:
        add(candidate)

    notice = lookup.notice
    if identification.identification_mode == "style_subject" and ordered:
        notice = (
            notice or "No strong catalog match."
        ) + " Showing visually related collection works for comparison."
    elif identification.identification_mode == "possible_match" and ordered:
        notice = notice or "Review possible matches before applying metadata."

    return lookup.model_copy(update={"candidates": ordered, "notice": notice})
