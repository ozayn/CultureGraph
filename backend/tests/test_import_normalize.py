import pytest
from pydantic import ValidationError

from app.services.import_normalize import (
    ImportNormalizationError,
    normalize_import_result,
    validate_normalized_import,
)


def test_normalize_import_result_accepts_entities_schema() -> None:
    raw = {
        "visit": {
            "museum_name": "NGA",
            "city": "Washington, DC",
            "visit_date": "2026-05-24",
            "summary": "Visit summary",
        },
        "entities": [
            {
                "entity_type": "artist",
                "name": "Thomas Moran",
                "description": "Landscape painter",
            }
        ],
    }
    normalized = normalize_import_result(raw)
    draft = validate_normalized_import(normalized)
    assert draft.entities[0].entity_type.value == "artist"
    assert draft.entities[0].name == "Thomas Moran"


def test_normalize_import_result_converts_legacy_artworks() -> None:
    raw = {
        "visit": {
            "museum_name": "NGA",
            "city": "Washington, DC",
            "visit_date": "2026-05-24",
            "summary": "Visit summary",
        },
        "artworks": [
            {
                "title": "The Grand Canyon of the Yellowstone",
                "artist": "Thomas Moran",
                "notes": "Dramatic western landscape",
                "concepts": ["Manifest Destiny"],
            }
        ],
    }
    normalized = normalize_import_result(raw)
    draft = validate_normalized_import(normalized)
    assert draft.entities[0].entity_type.value == "artwork"
    assert draft.entities[0].title == "The Grand Canyon of the Yellowstone"
    assert draft.entities[0].concepts == ["Manifest Destiny"]


def test_normalize_import_result_coerces_missing_optional_arrays() -> None:
    raw = {
        "visit": {
            "museum_name": "NGA",
            "city": "Washington, DC",
            "visit_date": "2026-05-24",
            "summary": "Visit summary",
        },
        "entities": [
            {
                "entity_type": "concept",
                "name": "Manifest Destiny",
            }
        ],
    }
    normalized = normalize_import_result(raw)
    entity = normalized["entities"][0]
    assert entity["related_entities"] == []
    assert entity["themes"] == []
    assert entity["suggested_annotations"] == []


def test_normalize_import_result_maps_invalid_entity_type_to_concept() -> None:
    raw = {
        "visit": {
            "museum_name": "NGA",
            "city": "Washington, DC",
            "visit_date": "2026-05-24",
            "summary": "Visit summary",
        },
        "entities": [
            {
                "entity_type": "not_a_real_type",
                "name": "Found objects",
            }
        ],
    }
    normalized = normalize_import_result(raw)
    draft = validate_normalized_import(normalized)
    assert draft.entities[0].entity_type.value == "concept"
    assert draft.entities[0].uncertainty


def test_normalize_import_result_maps_annotation_text_field() -> None:
    raw = {
        "visit": {
            "museum_name": "NGA",
            "city": "Washington, DC",
            "visit_date": "2026-05-24",
            "summary": "Visit summary",
        },
        "entities": [
            {
                "entity_type": "artwork",
                "name": "Reclining Liberty",
                "suggested_annotations": [
                    {"category": "history", "text": "Research the Brooklyn Waterfront reference."}
                ],
            }
        ],
    }
    normalized = normalize_import_result(raw)
    draft = validate_normalized_import(normalized)
    assert draft.entities[0].suggested_annotations[0].note == (
        "Research the Brooklyn Waterfront reference."
    )


def test_validate_normalized_import_rejects_missing_visit_fields() -> None:
    raw = normalize_import_result(
        {
            "visit": {"museum_name": "NGA"},
            "entities": [],
        },
        visit_defaults={
            "museum_name": "NGA",
            "city": "Washington, DC",
            "visit_date": "2026-05-24",
            "summary": "Imported museum notes.",
        },
    )
    draft = validate_normalized_import(raw)
    assert draft.visit.city == "Washington, DC"


def test_normalize_import_result_rejects_non_object_payload() -> None:
    with pytest.raises(ImportNormalizationError):
        normalize_import_result([])  # type: ignore[arg-type]
