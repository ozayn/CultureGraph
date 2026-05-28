"""Retrieval-assisted artwork identification — calibrate vision output with museum matches."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas import ArtworkLookupCandidateRead, ArtworkLookupResponse, IdentityEvidenceRead, ResearchDraft
from app.services.confidence_calibration import (
    STRONG_IDENTITY_MIN,
    VERIFIED_IDENTITY_MIN,
    calibrate_candidate_confidence,
)
from app.services.visual_analysis import (
    VisualAnalysis,
    build_visual_summary,
    collect_visual_keywords,
)
from app.sources.matching import normalize, score_artwork_entry_detailed


def _token_set(text: str) -> set[str]:
    return {token for token in normalize(text).split() if len(token) > 2}


def _draft_search_title(draft: ResearchDraft, lookup: ArtworkLookupResponse | None = None) -> str:
    if draft.possible_title:
        return draft.possible_title
    if draft.visual_hypothesis_title:
        return draft.visual_hypothesis_title
    if lookup and lookup.query_used:
        return lookup.query_used
    return ""


def _draft_search_artist(draft: ResearchDraft) -> str:
    return draft.possible_artist or draft.visual_hypothesis_artist or ""


def _has_plausible_hypothesis(draft: ResearchDraft) -> bool:
    title = (draft.visual_hypothesis_title or "").strip()
    artist = (draft.visual_hypothesis_artist or "").strip()
    return bool(title or artist)

IdentificationMode = Literal["catalog_match", "possible_match", "style_subject"]
ConfidenceLevel = Literal["high", "medium", "low"]

HIGH_IDENTITY = VERIFIED_IDENTITY_MIN
MEDIUM_IDENTITY = STRONG_IDENTITY_MIN


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
    visual_hypothesis_title: str | None = None
    visual_hypothesis_artist: str | None = None
    visual_hypothesis_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    hypothesis_source: str | None = None
    catalog_title: str | None = None
    catalog_artist: str | None = None
    visual_keywords: list[str] = Field(default_factory=list)
    catalog_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    identity_certainty: float | None = Field(default=None, ge=0.0, le=1.0)
    visual_similarity: float | None = Field(default=None, ge=0.0, le=1.0)
    match_explanation: str | None = None
    uncertainty_notes: list[str] = Field(default_factory=list)
    evidence: IdentityEvidenceRead | None = None


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


def _composition_overlap(visual: VisualAnalysis | None, candidate: ArtworkLookupCandidateRead) -> float:
    if not visual or not visual.composition:
        return 0.0
    return _visual_overlap_score(candidate, visual.composition[:4])


def _candidate_text_scores(
    candidate: ArtworkLookupCandidateRead,
    draft: ResearchDraft,
    lookup: ArtworkLookupResponse,
) -> tuple[float, float, float]:
    entry = {"title": candidate.title, "artist": candidate.artist}
    search_title = _draft_search_title(draft, lookup)
    search_artist = _draft_search_artist(draft)
    details = score_artwork_entry_detailed(
        entry,
        search_title,
        search_artist,
        draft.period_or_movement,
        strict_artist_gate=False,
    )
    return details.title_score, details.artist_score, details.combined


def rerank_candidates_with_visual(
    candidates: list[ArtworkLookupCandidateRead],
    visual: VisualAnalysis | None,
    visual_keywords: list[str],
    *,
    draft: ResearchDraft | None = None,
    lookup: ArtworkLookupResponse | None = None,
) -> list[ArtworkLookupCandidateRead]:
    if not candidates:
        return []

    draft = draft or ResearchDraft(
        short_summary="",
        historical_context="",
        visual_elements_to_notice=[],
        related_questions=[],
    )
    lookup = lookup or ArtworkLookupResponse(candidates=candidates, sources_searched=[])

    reranked: list[tuple[float, float, ArtworkLookupCandidateRead]] = []
    for candidate in candidates:
        overlap = _visual_overlap_score(candidate, visual_keywords)
        subject_overlap = 0.0
        if visual and visual.subject:
            subject_overlap = _visual_overlap_score(candidate, [visual.subject])
        composition_overlap = _composition_overlap(visual, candidate)

        title_score, artist_score, text_score = _candidate_text_scores(candidate, draft, lookup)
        match_reasons = list(candidate.match_reasons or [])
        if overlap >= 0.2:
            match_reasons.append("Visual keyword overlap")
        if subject_overlap >= 0.25:
            match_reasons.append("Subject description overlap")
        if composition_overlap >= 0.2:
            match_reasons.append("Composition overlap")

        calibrated = calibrate_candidate_confidence(
            title_score=title_score,
            artist_score=artist_score,
            text_score=text_score,
            candidate_title=candidate.title,
            candidate_artist=candidate.artist,
            search_title=_draft_search_title(draft, lookup),
            search_artist=_draft_search_artist(draft),
            has_title_query=bool(_draft_search_title(draft, lookup).strip()),
            match_reasons=match_reasons,
            ocr_label_text=draft.ocr_label_text,
            visual_subject=visual.subject if visual else None,
            visual_keywords=visual_keywords,
            visual_overlap=overlap,
            subject_overlap=subject_overlap,
            medium_mismatch=candidate.medium_match is False,
            attribution=bool(
                candidate.artist
                and re.search(
                    r"^(circle|school|workshop|follower|after|attributed)\b",
                    candidate.artist,
                    re.I,
                )
            ),
        )

        updated = candidate.model_copy(
            update={
                "confidence": calibrated.confidence,
                "identity_certainty": calibrated.identity_certainty,
                "visual_similarity": max(calibrated.visual_similarity, round(overlap, 2)),
                "low_confidence": calibrated.low_confidence,
                "match_tier": calibrated.match_tier,
                "match_reasons": list(calibrated.match_reasons),
                "match_explanation": calibrated.match_explanation,
            }
        )
        reranked.append(
            (
                calibrated.identity_certainty,
                updated.visual_similarity or 0.0,
                updated,
            )
        )

    reranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in reranked]


def _confidence_level(
    identity_certainty: float | None,
    *,
    low_flag: bool,
    verified: bool,
) -> ConfidenceLevel:
    if identity_certainty is None or low_flag:
        return "low"
    if identity_certainty >= HIGH_IDENTITY and verified:
        return "high"
    if identity_certainty >= MEDIUM_IDENTITY:
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

    reranked = rerank_candidates_with_visual(
        lookup.candidates,
        visual,
        keywords,
        draft=draft,
        lookup=lookup,
    )
    top = reranked[0] if reranked else None
    alternatives = reranked[1:4] if len(reranked) > 1 else []

    style = _style_assessment(visual, draft.period_or_movement)
    subject = _subject_assessment(visual)
    iconography = _iconography_notes(visual)

    identity_score = top.identity_certainty if top and top.identity_certainty is not None else (
        top.confidence if top else None
    )
    visual_score = top.visual_similarity if top else None
    low_flag = bool(top and top.low_confidence)
    verified = bool(
        top
        and (top.identity_certainty or 0) >= HIGH_IDENTITY
        and (
            bool(draft.ocr_label_text)
            or (
                (top.match_tier == "high")
                and not _has_plausible_hypothesis(draft)
            )
        )
    )
    level = _confidence_level(identity_score, low_flag=low_flag, verified=verified)

    match_reasons: list[str] = list(top.match_reasons) if top else []
    uncertainty_notes: list[str] = []
    match_explanation = top.match_explanation if top else None
    suggested_title: str | None = None
    suggested_artist: str | None = None
    catalog_title: str | None = None
    catalog_artist: str | None = None
    mode: IdentificationMode = "style_subject"
    display = ""

    if lookup.query_used:
        match_reasons.append(f"Searched collections for: {lookup.query_used}")

    if top and identity_score is not None and identity_score >= MEDIUM_IDENTITY and verified:
        mode = "catalog_match"
        artist_suffix = f" by {top.artist}" if top.artist else ""
        display = f"Collection match: {top.title}{artist_suffix} ({top.source_name})."
        suggested_title = top.title
        suggested_artist = top.artist
        catalog_title = top.title
        catalog_artist = top.artist
    elif top and identity_score is not None and identity_score >= MEDIUM_IDENTITY:
        mode = "possible_match"
        artist_suffix = f" by {top.artist}" if top.artist else ""
        style_bit = style or "this period/style"
        display = (
            f"Strong probable match: {top.title}{artist_suffix}. "
            f"Also consider {style_bit} — verify against the image and catalog record."
        )
        suggested_title = None
        suggested_artist = None
        uncertainty_notes.append("Identity is probable but not verified without label OCR or exact title confirmation.")
        level = "medium"
    elif top and visual_score is not None and visual_score >= 0.35:
        mode = "possible_match"
        style_bit = style or "this period/style"
        subject_bit = subject or "the depicted subject"
        display = (
            f"Visually similar to {_related_works_phrase(top)}. "
            f"Possibly {style_bit} depicting {subject_bit.rstrip('.')} — treat as a related work, not an exact match."
        )
        suggested_title = None
        suggested_artist = None
        level = "low"
        uncertainty_notes.append("Visual resemblance only — not enough evidence for exact identification.")
    elif top:
        mode = "possible_match"
        style_bit = style or "this period/style"
        subject_bit = subject or "the depicted subject"
        display = (
            f"Related work: possibly {style_bit} depicting {subject_bit.rstrip('.')} "
            f"— compare with {_related_works_phrase(top)} below."
        )
        suggested_title = None
        suggested_artist = None
        level = "low"
        uncertainty_notes.append("Possible stylistic connection only.")
    else:
        mode = "style_subject"
        style_bit = style or "an unidentified work in this style"
        subject_bit = subject or "an unidentified subject"
        hyp_title = draft.visual_hypothesis_title
        hyp_artist = draft.visual_hypothesis_artist
        if _has_plausible_hypothesis(draft):
            artist_suffix = f" by {hyp_artist}" if hyp_artist else ""
            title_bit = hyp_title or "Unknown title"
            display = (
                f"AI visual hypothesis: {title_bit}{artist_suffix}. "
                "Not verified against a collection record."
            )
            style_bit = style or "this period/style"
            display += f" Style: {style_bit}. Subject: {subject_bit.rstrip('.')}."
            uncertainty_notes.append("Visual hypothesis only — confirm against a museum catalog record.")
        else:
            display = (
                f"Possibly {style_bit}. Subject: {subject_bit.rstrip('.')}. "
                "No strong catalog match — style and iconography notes below."
            )
        suggested_title = None
        suggested_artist = None
        level = "low"

    if mode == "style_subject" and not _has_plausible_hypothesis(draft) and visual and visual.style_signals:
        display += f" Style resembles {', '.join(visual.style_signals[:2])}."

    evidence = None
    if top:
        title_score, artist_score, _ = _candidate_text_scores(top, draft, lookup)
        calibrated = calibrate_candidate_confidence(
            title_score=title_score,
            artist_score=artist_score,
            text_score=top.confidence,
            candidate_title=top.title,
            candidate_artist=top.artist,
            search_title=_draft_search_title(draft, lookup),
            search_artist=_draft_search_artist(draft),
            has_title_query=bool(_draft_search_title(draft, lookup).strip()),
            match_reasons=list(top.match_reasons or []),
            ocr_label_text=draft.ocr_label_text,
            visual_subject=visual.subject if visual else None,
            visual_keywords=keywords,
            visual_overlap=visual_score or 0.0,
        )
        evidence = IdentityEvidenceRead(
            exact_title_match=calibrated.evidence.exact_title_match,
            ocr_supported=calibrated.evidence.ocr_supported,
            artist_aligned=calibrated.evidence.artist_aligned,
            clip_similarity=calibrated.evidence.clip_similarity,
            reverse_image_similarity=calibrated.evidence.reverse_image_similarity,
            museum_context_match=calibrated.evidence.museum_context_match,
            composition_overlap=calibrated.evidence.composition_overlap,
            subject_overlap=calibrated.evidence.subject_overlap,
        )

    visual_hypothesis_title = None if mode == "catalog_match" else draft.visual_hypothesis_title
    visual_hypothesis_artist = None if mode == "catalog_match" else draft.visual_hypothesis_artist
    visual_hypothesis_confidence = (
        None if mode == "catalog_match" else draft.visual_hypothesis_confidence
    )
    hypothesis_source = None if mode == "catalog_match" else draft.hypothesis_source

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
        visual_hypothesis_title=visual_hypothesis_title,
        visual_hypothesis_artist=visual_hypothesis_artist,
        visual_hypothesis_confidence=visual_hypothesis_confidence,
        hypothesis_source=hypothesis_source,
        catalog_title=catalog_title,
        catalog_artist=catalog_artist,
        visual_keywords=keywords[:12],
        catalog_confidence=identity_score if mode == "catalog_match" else None,
        identity_certainty=identity_score,
        visual_similarity=visual_score,
        match_explanation=match_explanation,
        uncertainty_notes=uncertainty_notes[:4],
        evidence=evidence,
    )


def calibrate_research_draft(
    draft: ResearchDraft,
    identification: ArtworkIdentification,
    visual: VisualAnalysis | None = None,
) -> ResearchDraft:
    """Apply retrieval-assisted calibration — preserve unverified visual hypotheses."""
    visual = visual or draft.visual_analysis
    updated = draft.model_copy(deep=True)
    updated.short_summary = identification.display_summary

    updated.visual_hypothesis_title = draft.visual_hypothesis_title
    updated.visual_hypothesis_artist = draft.visual_hypothesis_artist
    updated.visual_hypothesis_confidence = draft.visual_hypothesis_confidence
    updated.hypothesis_source = draft.hypothesis_source

    if identification.identification_mode == "catalog_match":
        updated.catalog_title = identification.catalog_title or identification.suggested_title
        updated.catalog_artist = identification.catalog_artist or identification.suggested_artist
        updated.catalog_confidence = identification.identity_certainty
        if identification.suggested_title:
            updated.possible_title = identification.suggested_title
        if identification.suggested_artist:
            updated.possible_artist = identification.suggested_artist
        updated.confidence = identification.identity_certainty or updated.confidence
    else:
        updated.catalog_title = None
        updated.catalog_artist = None
        updated.catalog_confidence = None
        if draft.ocr_label_text:
            updated.possible_title = draft.possible_title
            updated.possible_artist = draft.possible_artist
        else:
            updated.possible_title = None
            updated.possible_artist = None
        if identification.identity_certainty is not None:
            updated.confidence = min(
                identification.identity_certainty,
                draft.confidence or identification.identity_certainty,
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
        notice = notice or "Review related and visually similar matches before applying metadata."

    return lookup.model_copy(update={"candidates": ordered, "notice": notice})
