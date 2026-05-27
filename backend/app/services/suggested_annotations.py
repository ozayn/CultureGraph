"""Parse, normalize, and persist AI suggested annotation status on research notes."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import TypeAdapter

from app.models import Annotation, ResearchNote
from app.schemas import AiSuggestedAnnotation

SuggestedAnnotationStatus = Literal["pending", "accepted", "dismissed"]

_STATUS_ADAPTER = TypeAdapter(SuggestedAnnotationStatus)
_ANNOTATION_ADAPTER = TypeAdapter(list[AiSuggestedAnnotation])


def _normalize_status(raw: object) -> SuggestedAnnotationStatus:
    if isinstance(raw, str):
        try:
            return _STATUS_ADAPTER.validate_python(raw.strip().lower())
        except Exception:
            pass
    return "pending"


def _suggestion_key(category: str, note: str) -> str:
    collapsed = re.sub(r"\s+", " ", note.strip().lower())
    return f"{category.strip().lower()}::{collapsed}"


def normalize_suggested_annotation(raw: dict[str, Any]) -> AiSuggestedAnnotation | None:
    if not isinstance(raw, dict):
        return None

    note = raw.get("note") or raw.get("text")
    if not isinstance(note, str) or not note.strip():
        return None

    try:
        item = AiSuggestedAnnotation.model_validate(raw)
    except Exception:
        return None

    status = _normalize_status(raw.get("status", "pending"))
    accepted_id = raw.get("accepted_annotation_id")
    payload = item.model_dump(mode="json")
    payload["status"] = status
    if isinstance(accepted_id, int):
        payload["accepted_annotation_id"] = accepted_id
    else:
        payload["accepted_annotation_id"] = None
    return AiSuggestedAnnotation.model_validate(payload)


def parse_suggested_annotations_json(value: str | None) -> list[AiSuggestedAnnotation]:
    if not value or not value.strip():
        return []

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []

    if not isinstance(parsed, list):
        return []

    items: list[AiSuggestedAnnotation] = []
    for raw in parsed:
        if not isinstance(raw, dict):
            continue
        item = normalize_suggested_annotation(raw)
        if item is not None:
            items.append(item)
    return items


def infer_accepted_suggestions(
    suggestions: list[AiSuggestedAnnotation],
    annotations: list[Annotation],
) -> list[AiSuggestedAnnotation]:
    if not suggestions or not annotations:
        return suggestions

    by_key: dict[str, Annotation] = {}
    for annotation in annotations:
        key = _suggestion_key(annotation.category, annotation.text)
        by_key[key] = annotation

    updated: list[AiSuggestedAnnotation] = []
    changed = False
    for suggestion in suggestions:
        status = _normalize_status(getattr(suggestion, "status", "pending"))
        accepted_id = getattr(suggestion, "accepted_annotation_id", None)

        if status in {"accepted", "dismissed"}:
            updated.append(suggestion)
            continue

        match = by_key.get(_suggestion_key(suggestion.category, suggestion.note))
        if match is not None:
            changed = True
            payload = suggestion.model_dump(mode="json")
            payload["status"] = "accepted"
            payload["accepted_annotation_id"] = match.id
            updated.append(AiSuggestedAnnotation.model_validate(payload))
        else:
            payload = suggestion.model_dump(mode="json")
            payload["status"] = "pending"
            payload["accepted_annotation_id"] = None
            updated.append(AiSuggestedAnnotation.model_validate(payload))

    return updated if changed else suggestions


def pending_suggestions(suggestions: list[AiSuggestedAnnotation]) -> list[AiSuggestedAnnotation]:
    return [
        item
        for item in suggestions
        if _normalize_status(getattr(item, "status", "pending")) == "pending"
    ]


def serialize_suggested_annotations(suggestions: list[AiSuggestedAnnotation]) -> str:
    normalized: list[dict[str, Any]] = []
    for item in suggestions:
        payload = item.model_dump(mode="json")
        payload["status"] = _normalize_status(payload.get("status", "pending"))
        accepted_id = payload.get("accepted_annotation_id")
        payload["accepted_annotation_id"] = (
            accepted_id if isinstance(accepted_id, int) else None
        )
        normalized.append(payload)
    return json.dumps(normalized)


def ensure_pending_defaults(suggestions: list[AiSuggestedAnnotation]) -> list[AiSuggestedAnnotation]:
    return _ANNOTATION_ADAPTER.validate_python(
        [
            AiSuggestedAnnotation.model_validate(
                {
                    **item.model_dump(mode="json"),
                    "status": "pending",
                    "accepted_annotation_id": None,
                }
            )
            for item in suggestions
        ]
    )


def load_note_suggestions(
    note: ResearchNote,
    annotations: list[Annotation] | None = None,
) -> list[AiSuggestedAnnotation]:
    parsed = parse_suggested_annotations_json(note.suggested_annotations)
    if annotations:
        parsed = infer_accepted_suggestions(parsed, annotations)
    return parsed


def save_note_suggestions(note: ResearchNote, suggestions: list[AiSuggestedAnnotation]) -> None:
    note.suggested_annotations = serialize_suggested_annotations(suggestions)
