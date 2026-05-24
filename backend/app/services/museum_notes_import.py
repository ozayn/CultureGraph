import re
from datetime import date
from typing import Protocol

from anthropic import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncAnthropic,
    AuthenticationError,
    RateLimitError,
)
from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.schemas import (
    AnnotationCategory,
    ConceptLinkDraft,
    CulturalEntityType,
    ImportedEntityDraft,
    MuseumNotesImportRequest,
    MuseumNotesImportResponse,
    SuggestedAnnotationDraft,
    VisitImportDraft,
)
from app.services.artwork_note_parser import ParsedArtworkFields, parse_artwork_fields
from app.services.claude_json import JsonExtractionError, extract_json_object, sanitize_response_preview
from app.services.research import ResearchConfigurationError, ResearchProviderError

IMPORT_TOOL_NAME = "submit_museum_notes_import"
IMPORT_FALLBACK_WARNING = (
    "Claude response could not be parsed; used local fallback extraction."
)

IMPORT_TOOL_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "visit": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "museum_name": {"type": "string"},
                "city": {"type": "string"},
                "visit_date": {"type": "string"},
                "summary": {"type": "string"},
            },
            "required": ["museum_name", "city", "visit_date", "summary"],
        },
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": [
                            "artwork",
                            "artist",
                            "concept",
                            "movement",
                            "technique",
                            "material",
                            "historical_event",
                            "symbol",
                            "architecture",
                            "museum_space",
                            "political_idea",
                        ],
                    },
                    "name": {"type": "string"},
                    "description": {"type": ["string", "null"]},
                    "related_entities": {"type": "array", "items": {"type": "string"}},
                    "uncertainty": {"type": ["string", "null"]},
                    "title": {"type": ["string", "null"]},
                    "artist": {"type": ["string", "null"]},
                    "period_or_year": {"type": ["string", "null"]},
                    "medium": {"type": ["string", "null"]},
                    "display_label": {"type": ["string", "null"]},
                    "themes": {"type": "array", "items": {"type": "string"}},
                    "concepts": {"type": "array", "items": {"type": "string"}},
                    "movements": {"type": "array", "items": {"type": "string"}},
                    "historical_events": {"type": "array", "items": {"type": "string"}},
                    "suggested_annotations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "category": {
                                    "type": "string",
                                    "enum": [
                                        "history",
                                        "symbol",
                                        "observation",
                                        "composition",
                                        "question",
                                    ],
                                },
                                "note": {"type": "string"},
                            },
                            "required": ["category", "note"],
                        },
                    },
                },
                "required": ["entity_type", "name"],
            },
        },
        "concept_links": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "relationship": {"type": "string"},
                },
                "required": ["source", "target", "relationship"],
            },
        },
    },
    "required": ["visit", "entities", "concept_links"],
}

IMPORT_JSON_SCHEMA_PROMPT = """\
Return ONLY valid JSON matching the required schema.
- No markdown.
- No code fences.
- No explanation before or after the JSON.
- No trailing comments.
- Use double quotes only.
- Use null for unknown values instead of placeholder strings like "unknown" or "N/A".

Exact shape:
{
  "visit": {
    "museum_name": string,
    "city": string,
    "visit_date": "YYYY-MM-DD",
    "summary": string
  },
  "entities": [
    {
      "entity_type": "artwork" | "artist" | "concept" | "movement" | "technique" | "material" | "historical_event" | "symbol" | "architecture" | "museum_space" | "political_idea",
      "name": string,
      "description": string or null,
      "related_entities": [string, ...],
      "uncertainty": string or null,
      "title": string or null,
      "artist": string or null,
      "period_or_year": string or null,
      "medium": string or null,
      "display_label": string or null,
      "themes": [string, ...],
      "concepts": [string, ...],
      "movements": [string, ...],
      "historical_events": [string, ...],
      "suggested_annotations": [
        {"category": "history" | "symbol" | "observation" | "composition" | "question", "note": string}
      ]
    }
  ],
  "concept_links": [
    {"source": string, "target": string, "relationship": string}
  ]
}

Rules:
- Classify each distinct note entry by entity_type before filling fields.
- Do NOT force every line into artwork. Artists, concepts, movements, materials, techniques,
  historical events, symbols, architecture, museum spaces, and political ideas are valid entries.
- Extract only what appears in the pasted museum notes. Do not invent titles, dates, or artists.
- Do not invent artwork titles. Extract exact titles only when they appear explicitly in the notes.
- Preserve uncertainty in description or uncertainty when classification or details are unclear.
- related_entities: names of other extracted entities this entry connects to.
- For artwork entities, optionally populate artist, concepts, movements, historical_events.
- suggested_annotations: 0–3 ideas tied to details actually mentioned (artwork entries only).
- concept_links: only when the notes explicitly connect entities.
- visit.summary: a short notebook-style overview of the visit based on the notes.
"""


class _ClaudeImportPayload(BaseModel):
    visit: VisitImportDraft
    entities: list[ImportedEntityDraft]
    concept_links: list[ConceptLinkDraft] = Field(default_factory=list)


class MuseumNotesImportProvider(Protocol):
    async def extract(self, request: MuseumNotesImportRequest) -> MuseumNotesImportResponse:
        ...


_ARTIST_HINTS: list[dict] = [
    {
        "match": ("grandma moses",),
        "artist": "Grandma Moses",
        "themes": ["folk art", "American scenes"],
    },
    {
        "match": ("thomas moran", "moran"),
        "artist": "Thomas Moran",
        "themes": ["western landscape"],
        "related": ["Manifest Destiny"],
    },
    {
        "match": ("sanford biggers", "biggers"),
        "artist": "Sanford Biggers",
        "themes": ["contemporary sculpture"],
    },
    {
        "match": ("alexis rockman", "rockman"),
        "artist": "Alexis Rockman",
        "themes": ["apocalyptic landscape"],
        "related": ["Manifest Destiny"],
    },
    {
        "match": ("sam gilliam", "gilliam"),
        "artist": "Sam Gilliam",
        "themes": ["abstraction", "installation"],
    },
    {
        "match": ("leonardo drew", "drew"),
        "artist": "Leonardo Drew",
        "themes": ["assemblage"],
    },
]

_TYPED_KEYWORDS: list[tuple[str, CulturalEntityType, str | None]] = [
    ("manifest destiny", CulturalEntityType.political_idea, "Manifest Destiny"),
    ("wpa", CulturalEntityType.historical_event, "WPA"),
    ("works progress administration", CulturalEntityType.historical_event, "WPA"),
    ("gesso", CulturalEntityType.material, "Gesso"),
    ("unprimed canvas", CulturalEntityType.technique, "Unprimed canvas"),
    ("dc color school", CulturalEntityType.movement, "DC Color School"),
    ("color school", CulturalEntityType.movement, "DC Color School"),
    ("clenched fist", CulturalEntityType.symbol, "Clenched fist"),
    ("lincoln gallery", CulturalEntityType.museum_space, "Lincoln Gallery"),
    ("found object", CulturalEntityType.material, "Found objects"),
    ("found objects", CulturalEntityType.concept, "Found objects"),
    ("draped canvas", CulturalEntityType.technique, "Draped canvas"),
    ("brooklyn waterfront", CulturalEntityType.concept, "Brooklyn Waterfront"),
]


def _default_visit_date(request: MuseumNotesImportRequest) -> str:
    if request.visit_date:
        return request.visit_date.isoformat()
    return date.today().isoformat()


def _split_note_blocks(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    blocks: list[str] = []

    for line in lines:
        cleaned = re.sub(r"^[\-*•\d]+[\.\)]\s*", "", line).strip()
        if not cleaned:
            continue

        lowered = cleaned.lower()
        if (
            len(cleaned.split()) <= 5
            and not _match_artist_hint(cleaned)
            and ("museum" in lowered or "visit notes" in lowered)
        ):
            continue

        blocks.append(cleaned)

    if not blocks and text.strip():
        blocks = [text.strip()]

    return blocks


def _match_artist_hint(block: str) -> dict | None:
    lowered = block.lower()
    for hint in _ARTIST_HINTS:
        if any(token in lowered for token in hint["match"]):
            return hint
    return None


def _match_typed_keyword(block: str) -> tuple[CulturalEntityType, str] | None:
    lowered = block.lower()
    for keyword, entity_type, name in _TYPED_KEYWORDS:
        if keyword in lowered:
            return entity_type, name
    return None


def _split_compound_block(block: str) -> list[str]:
    if " and " not in block.lower():
        return [block]

    parts = re.split(r"\s+and\s+", block, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) != 2:
        return [block]

    left, right = parts[0].strip(), parts[1].strip()
    if not left or not right:
        return [block]

    right_match = _match_typed_keyword(right) or _match_typed_keyword(f"x {right}")
    if right_match or len(right.split()) <= 4:
        return [left, right]
    return [block]


def _suggested_annotations_for_block(block: str, concepts: list[str]) -> list[SuggestedAnnotationDraft]:
    annotations: list[SuggestedAnnotationDraft] = []
    if concepts:
        annotations.append(
            SuggestedAnnotationDraft(
                category=AnnotationCategory.history,
                note=f"Research how {concepts[0]} frames this work.",
            )
        )
    annotations.append(
        SuggestedAnnotationDraft(
            category=AnnotationCategory.observation,
            note=f"Revisit this note in the gallery: {block[:120]}{'…' if len(block) > 120 else ''}",
        )
    )
    if "?" in block:
        annotations.append(
            SuggestedAnnotationDraft(
                category=AnnotationCategory.question,
                note="What question from your notes still needs verifying?",
            )
        )
    return annotations[:3]


def _build_artwork_entity(
    block: str,
    parsed: ParsedArtworkFields,
    hint: dict | None,
) -> ImportedEntityDraft:
    artist = parsed.artist or (hint["artist"] if hint else None)
    title = parsed.title
    concepts = list(hint.get("related", [])) if hint else []
    for keyword, _, name in _TYPED_KEYWORDS:
        if keyword in block.lower() and name and name not in concepts:
            concepts.append(name)

    display_label = parsed.display_label or title or artist or parsed.descriptive_label or block[:80]
    name = title or display_label or artist or block[:80]

    return ImportedEntityDraft(
        entity_type=CulturalEntityType.artwork,
        name=name,
        description=block,
        related_entities=[artist] if artist else [],
        title=title,
        artist=artist,
        period_or_year=parsed.period_or_year,
        medium=parsed.medium,
        display_label=display_label,
        themes=list(hint.get("themes", [])) if hint else [],
        concepts=concepts,
        suggested_annotations=_suggested_annotations_for_block(block, concepts),
        uncertainty="Title not explicit in notes." if not title and artist else None,
    )


def _build_artist_entity(block: str, artist: str, hint: dict | None) -> ImportedEntityDraft:
    related = list(hint.get("related", [])) if hint else []
    return ImportedEntityDraft(
        entity_type=CulturalEntityType.artist,
        name=artist,
        description=block,
        related_entities=related,
        themes=list(hint.get("themes", [])) if hint else [],
    )


def _build_typed_entity(
    block: str,
    entity_type: CulturalEntityType,
    name: str,
    related: list[str] | None = None,
) -> ImportedEntityDraft:
    return ImportedEntityDraft(
        entity_type=entity_type,
        name=name,
        description=block if block.lower() != name.lower() else None,
        related_entities=related or [],
    )


def _classify_block(block: str) -> list[ImportedEntityDraft]:
    hint = _match_artist_hint(block)
    parsed = parse_artwork_fields(block)
    typed = _match_typed_keyword(block)

    subblocks = _split_compound_block(block)
    if len(subblocks) > 1:
        entities: list[ImportedEntityDraft] = []
        for subblock in subblocks:
            entities.extend(_classify_block(subblock))
        return entities

    if typed:
        entity_type, name = typed
        if not parsed.title and (
            not parsed.artist or parsed.artist.strip().lower() == name.lower()
        ):
            related = [hint["artist"]] if hint else []
            return [_build_typed_entity(block, entity_type, name, related)]

    if parsed.title:
        return [_build_artwork_entity(block, parsed, hint)]

    if hint:
        artist = hint["artist"]
        if parsed.artist and parsed.artist != artist:
            artist = parsed.artist
        if len(block.split()) > 6 or any(
            word in block.lower()
            for word in ("scene", "canvas", "landscape", "print", "sculpture", "painting")
        ):
            return [_build_artwork_entity(block, parsed, hint)]
        return [_build_artist_entity(block, artist, hint)]

    if parsed.artist:
        return [_build_artist_entity(block, parsed.artist, None)]

    if typed:
        entity_type, name = typed
        return [_build_typed_entity(block, entity_type, name)]

    if len(block.split()) < 4:
        return []

    return [
        ImportedEntityDraft(
            entity_type=CulturalEntityType.concept,
            name=block[:80],
            description=block,
            uncertainty="Could not confidently classify this entry.",
        )
    ]


def _dedupe_entities(entities: list[ImportedEntityDraft]) -> list[ImportedEntityDraft]:
    seen: set[tuple[str, str]] = set()
    unique: list[ImportedEntityDraft] = []
    for entity in entities:
        key = (entity.entity_type.value, entity.name.strip().lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(entity)
    return unique


def _concept_links_from_entities(entities: list[ImportedEntityDraft]) -> list[ConceptLinkDraft]:
    links: list[ConceptLinkDraft] = []
    seen: set[tuple[str, str]] = set()

    for entity in entities:
        if entity.entity_type == CulturalEntityType.artwork:
            source = entity.artist or entity.title or entity.name
            targets = [
                *entity.concepts,
                *entity.movements,
                *entity.historical_events,
                *entity.related_entities,
            ]
            for target in targets:
                key = (source, target)
                if not source or key in seen:
                    continue
                seen.add(key)
                links.append(ConceptLinkDraft(source=source, target=target, relationship="context"))
            continue

        for related in entity.related_entities:
            key = (entity.name, related)
            if key in seen:
                continue
            seen.add(key)
            links.append(
                ConceptLinkDraft(source=entity.name, target=related, relationship="related")
            )

    return links


class MockMuseumNotesImportProvider:
    async def extract(self, request: MuseumNotesImportRequest) -> MuseumNotesImportResponse:
        blocks = _split_note_blocks(request.text)
        entities: list[ImportedEntityDraft] = []

        for block in blocks:
            entities.extend(_classify_block(block))

        entities = _dedupe_entities(entities)

        if not entities and request.text.strip():
            entities.append(
                ImportedEntityDraft(
                    entity_type=CulturalEntityType.concept,
                    name="Unclassified notes",
                    description=request.text.strip(),
                    uncertainty="Review pasted notes and classify individual entries.",
                    suggested_annotations=[
                        SuggestedAnnotationDraft(
                            category=AnnotationCategory.observation,
                            note="Review pasted notes and identify individual cultural entries.",
                        )
                    ],
                )
            )

        type_counts: dict[str, int] = {}
        for entity in entities:
            type_counts[entity.entity_type.value] = type_counts.get(entity.entity_type.value, 0) + 1

        summary_parts = [
            f"Imported notebook entries for {request.default_museum}.",
            f"{len(entities)} entr{'ies' if len(entities) != 1 else 'y'} extracted across "
            f"{len(type_counts)} type{'s' if len(type_counts) != 1 else ''}.",
        ]

        visit = VisitImportDraft(
            museum_name=request.default_museum,
            city=request.default_city,
            visit_date=_default_visit_date(request),
            summary=" ".join(summary_parts),
        )

        concept_links = _concept_links_from_entities(entities)

        return MuseumNotesImportResponse(
            visit=visit,
            entities=entities,
            concept_links=concept_links,
            source="mock",
        )


def _read_claude_import_payload(message: object) -> dict:
    content = getattr(message, "content", [])
    for block in content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == IMPORT_TOOL_NAME:
            payload = getattr(block, "input", None)
            if isinstance(payload, dict):
                return payload
            raise JsonExtractionError("Claude tool response was not a JSON object.")

    text_blocks = [block.text for block in content if getattr(block, "type", None) == "text"]
    if text_blocks:
        return extract_json_object(text_blocks[0])

    raise JsonExtractionError("Claude returned an empty response.")


async def _fallback_to_mock_import(request: MuseumNotesImportRequest) -> MuseumNotesImportResponse:
    fallback = await MockMuseumNotesImportProvider().extract(request)
    return fallback.model_copy(
        update={
            "source": "mock",
            "ai_warning": IMPORT_FALLBACK_WARNING,
        }
    )


class ClaudeMuseumNotesImportProvider:
    def __init__(self, api_key: str) -> None:
        if not api_key.strip():
            raise ResearchConfigurationError(
                "ANTHROPIC_API_KEY is set but empty. Add a valid key or remove it to use mock import."
            )

        self._client = AsyncAnthropic(
            api_key=api_key.strip(),
            timeout=settings.anthropic_timeout_seconds,
            max_retries=0,
        )

    async def extract(self, request: MuseumNotesImportRequest) -> MuseumNotesImportResponse:
        visit_date = _default_visit_date(request)
        prompt = "\n".join(
            [
                "Convert the following rough museum notes into structured CultureGraph draft data.",
                "Use the submit_museum_notes_import tool with valid JSON only.",
                "",
                f"Default museum: {request.default_museum}",
                f"Default city: {request.default_city}",
                f"Default visit date (use unless notes specify another): {visit_date}",
                "",
                "Museum notes:",
                request.text.strip(),
                "",
                IMPORT_JSON_SCHEMA_PROMPT,
            ]
        )

        try:
            message = await self._client.messages.create(
                model=settings.anthropic_model,
                max_tokens=settings.anthropic_max_tokens,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
                tools=[
                    {
                        "name": IMPORT_TOOL_NAME,
                        "description": (
                            "Submit structured museum notes import data matching the CultureGraph schema."
                        ),
                        "input_schema": IMPORT_TOOL_SCHEMA,
                    }
                ],
                tool_choice={"type": "tool", "name": IMPORT_TOOL_NAME},
            )
        except AuthenticationError as exc:
            raise ResearchConfigurationError(
                "ANTHROPIC_API_KEY is invalid or unauthorized. Check the key in your environment."
            ) from exc
        except APITimeoutError as exc:
            raise ResearchProviderError(
                f"Claude request timed out after {settings.anthropic_timeout_seconds:g}s."
            ) from exc
        except RateLimitError as exc:
            raise ResearchProviderError(
                "Claude rate limit reached. Wait a moment and try again."
            ) from exc
        except APIConnectionError as exc:
            raise ResearchProviderError(
                "Could not reach the Anthropic API. Check your network connection."
            ) from exc
        except APIStatusError as exc:
            raise ResearchProviderError(
                f"Anthropic API error ({exc.status_code}): {exc.message}"
            ) from exc

        try:
            payload = _read_claude_import_payload(message)
            parsed = _ClaudeImportPayload.model_validate(payload)
        except (JsonExtractionError, ValidationError) as exc:
            preview = sanitize_response_preview(
                "".join(
                    block.text
                    for block in message.content
                    if getattr(block, "type", None) == "text"
                )
            )
            if settings.is_production:
                return await _fallback_to_mock_import(request)

            if isinstance(exc, ValidationError):
                raise ResearchProviderError(
                    "Claude response did not match the expected museum notes import schema. "
                    f"Preview: {preview or '[tool response]'}"
                ) from exc

            raise ResearchProviderError(f"{exc} Preview: {preview or '[tool response]'}") from exc

        return MuseumNotesImportResponse(
            visit=parsed.visit,
            entities=parsed.entities,
            concept_links=parsed.concept_links,
            source="claude",
        )


def get_museum_notes_import_provider() -> MuseumNotesImportProvider:
    api_key = settings.anthropic_api_key
    if not api_key or not api_key.strip():
        return MockMuseumNotesImportProvider()

    return ClaudeMuseumNotesImportProvider(api_key)
