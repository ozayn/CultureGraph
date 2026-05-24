"""Normalize Claude import payloads into the current multi-entity schema."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from app.schemas import (
    ConceptLinkDraft,
    CulturalEntityType,
    ImportedEntityDraft,
    VisitImportDraft,
)

logger = logging.getLogger(__name__)

VALID_ENTITY_TYPES = {item.value for item in CulturalEntityType}
ENTITY_LIST_FIELDS = (
    "related_entities",
    "themes",
    "concepts",
    "movements",
    "historical_events",
)
ANNOTATION_CATEGORIES = {
    "observation",
    "symbol",
    "history",
    "question",
    "composition",
}


class ImportNormalizationError(ValueError):
    """Raised when an import payload cannot be normalized."""


class NormalizedImportDraft:
    """Validated import draft returned by normalize_import_result."""

    def __init__(
        self,
        *,
        visit: VisitImportDraft,
        entities: list[ImportedEntityDraft],
        concept_links: list[ConceptLinkDraft],
    ) -> None:
        self.visit = visit
        self.entities = entities
        self.concept_links = concept_links


def _coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if item is not None and str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _coerce_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_annotation(raw: Any) -> dict[str, str] | None:
    if not isinstance(raw, dict):
        return None

    note = raw.get("note") or raw.get("text")
    category = raw.get("category")
    if not note or not category:
        return None

    category_text = str(category).strip().lower()
    if category_text not in ANNOTATION_CATEGORIES:
        category_text = "observation"

    note_text = str(note).strip()
    if not note_text:
        return None

    return {"category": category_text, "note": note_text}


def _normalize_entity(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ImportNormalizationError("Each entity must be an object.")

    entity = dict(raw)
    entity_type = _coerce_optional_str(entity.get("entity_type")) or "artwork"
    if entity_type not in VALID_ENTITY_TYPES:
        entity_type = "concept"
        entity["uncertainty"] = _coerce_optional_str(entity.get("uncertainty")) or (
            f"Adjusted unknown entity_type '{raw.get('entity_type')}' to concept."
        )
    entity["entity_type"] = entity_type

    name = (
        _coerce_optional_str(entity.get("name"))
        or _coerce_optional_str(entity.get("display_label"))
        or _coerce_optional_str(entity.get("title"))
        or _coerce_optional_str(entity.get("artist"))
    )
    if not name:
        raise ImportNormalizationError("Entity is missing a usable name.")
    entity["name"] = name

    if entity.get("description") is None and entity.get("notes") is not None:
        entity["description"] = _coerce_optional_str(entity.get("notes"))

    for field in ENTITY_LIST_FIELDS:
        entity[field] = _coerce_str_list(entity.get(field))

    annotations = entity.get("suggested_annotations")
    normalized_annotations: list[dict[str, str]] = []
    if isinstance(annotations, list):
        for item in annotations:
            normalized = _normalize_annotation(item)
            if normalized:
                normalized_annotations.append(normalized)
    entity["suggested_annotations"] = normalized_annotations

    for field in (
        "description",
        "uncertainty",
        "title",
        "artist",
        "period_or_year",
        "medium",
        "display_label",
    ):
        entity[field] = _coerce_optional_str(entity.get(field))

    return entity


def _artwork_to_entity(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ImportNormalizationError("Each artwork must be an object.")

    return _normalize_entity(
        {
            "entity_type": "artwork",
            "name": raw.get("display_label") or raw.get("title") or raw.get("artist"),
            "description": raw.get("notes"),
            "title": raw.get("title"),
            "artist": raw.get("artist"),
            "period_or_year": raw.get("period_or_year"),
            "medium": raw.get("medium"),
            "display_label": raw.get("display_label"),
            "themes": raw.get("themes"),
            "concepts": raw.get("concepts"),
            "suggested_annotations": raw.get("suggested_annotations"),
            "uncertainty": None if raw.get("title") else "Title not explicit in notes.",
        }
    )


def _normalize_visit(raw: Any, defaults: dict[str, str] | None = None) -> dict[str, Any]:
    defaults = defaults or {}
    visit = raw if isinstance(raw, dict) else {}

    museum_name = _coerce_optional_str(visit.get("museum_name")) or defaults.get("museum_name")
    city = _coerce_optional_str(visit.get("city")) or defaults.get("city")
    visit_date = _coerce_optional_str(visit.get("visit_date")) or defaults.get("visit_date")
    summary = _coerce_optional_str(visit.get("summary")) or defaults.get("summary") or (
        "Imported museum notes."
    )

    missing = [field for field, value in [
        ("museum_name", museum_name),
        ("city", city),
        ("visit_date", visit_date),
    ] if not value]
    if missing:
        raise ImportNormalizationError(f"visit missing required fields: {', '.join(missing)}")

    return {
        "museum_name": museum_name,
        "city": city,
        "visit_date": visit_date,
        "summary": summary,
    }


def _normalize_concept_links(raw: Any) -> list[dict[str, str]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        return []

    links: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        source = _coerce_optional_str(item.get("source"))
        target = _coerce_optional_str(item.get("target"))
        relationship = _coerce_optional_str(item.get("relationship")) or "related"
        if source and target:
            links.append(
                {"source": source, "target": target, "relationship": relationship}
            )
    return links


def _is_legacy_artwork(item: dict[str, Any]) -> bool:
    if "entity_type" in item:
        return False
    return any(key in item for key in ("title", "artist", "notes", "display_label", "period_or_year"))


def normalize_import_result(
    raw: dict[str, Any],
    *,
    visit_defaults: dict[str, str] | None = None,
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ImportNormalizationError("Import payload must be a JSON object.")

    normalized: dict[str, Any] = dict(raw)
    normalized.pop("ai_warning", None)

    entities_raw: Any
    if "entities" in normalized:
        entities_raw = normalized["entities"]
    elif "artworks" in normalized:
        entities_raw = normalized.pop("artworks")
    else:
        entities_raw = []

    if not isinstance(entities_raw, list):
        raise ImportNormalizationError("entities must be an array.")

    normalized.pop("artworks", None)

    entities: list[dict[str, Any]] = []
    for item in entities_raw:
        if not isinstance(item, dict):
            continue
        try:
            if _is_legacy_artwork(item):
                entities.append(_artwork_to_entity(item))
            else:
                entities.append(_normalize_entity(item))
        except ImportNormalizationError:
            entities.append(
                _normalize_entity(
                    {
                        **item,
                        "entity_type": "concept",
                        "name": item.get("name")
                        or item.get("title")
                        or item.get("artist")
                        or "Unclassified entry",
                    }
                )
            )

    normalized["entities"] = entities
    normalized["concept_links"] = _normalize_concept_links(normalized.get("concept_links"))
    normalized["visit"] = _normalize_visit(normalized.get("visit"), visit_defaults)

    return normalized


def validate_normalized_import(raw: dict[str, Any]) -> NormalizedImportDraft:
    from pydantic import BaseModel, Field

    class _Payload(BaseModel):
        visit: VisitImportDraft
        entities: list[ImportedEntityDraft]
        concept_links: list[ConceptLinkDraft] = Field(default_factory=list)

    parsed = _Payload.model_validate(raw)
    return NormalizedImportDraft(
        visit=parsed.visit,
        entities=parsed.entities,
        concept_links=parsed.concept_links,
    )


def summarize_validation_failure(raw: dict[str, Any] | None, exc: Exception) -> str:
    keys = sorted(raw.keys()) if isinstance(raw, dict) else []
    if isinstance(exc, ValidationError):
        details = "; ".join(
            f"{'.'.join(str(part) for part in error.get('loc', ()))}: {error.get('msg')}"
            for error in exc.errors()[:5]
        )
        return f"keys={keys}; validation={details or exc}"
    return f"keys={keys}; error={exc}"


def log_import_validation_failure(raw: dict[str, Any] | None, exc: Exception) -> None:
    logger.warning("Claude import normalization failed: %s", summarize_validation_failure(raw, exc))
