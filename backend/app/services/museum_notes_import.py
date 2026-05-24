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
    ArtworkImportDraft,
    ConceptLinkDraft,
    MuseumNotesImportRequest,
    MuseumNotesImportResponse,
    SuggestedAnnotationDraft,
    VisitImportDraft,
)
from app.services.claude_research import _extract_json
from app.services.research import ResearchConfigurationError, ResearchProviderError

IMPORT_JSON_SCHEMA_PROMPT = """\
Return ONLY a single JSON object (no markdown fences, no commentary) with this exact shape:
{
  "visit": {
    "museum_name": string,
    "city": string,
    "visit_date": "YYYY-MM-DD",
    "summary": string
  },
  "artworks": [
    {
      "title": string or null,
      "artist": string or null,
      "period_or_year": string or null,
      "medium": string or null,
      "notes": string or null,
      "themes": [string, ...],
      "concepts": [string, ...],
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
- Extract only what appears in the pasted museum notes. Do not invent titles, dates, or artists.
- If an artwork title is unknown, set title to null and put the description in notes.
- Preserve uncertainty in notes and summary when details are unclear.
- suggested_annotations: 1–3 ideas tied to details actually mentioned in the notes.
- concept_links: only when the notes explicitly connect an artist, artwork, or idea to a concept.
- visit.summary: a short notebook-style overview of the visit based on the notes.
"""


class _ClaudeImportPayload(BaseModel):
    visit: VisitImportDraft
    artworks: list[ArtworkImportDraft]
    concept_links: list[ConceptLinkDraft] = Field(default_factory=list)


class MuseumNotesImportProvider(Protocol):
    async def extract(self, request: MuseumNotesImportRequest) -> MuseumNotesImportResponse:
        ...


_ARTIST_HINTS: list[dict] = [
    {
        "match": ("grandma moses",),
        "artist": "Grandma Moses",
        "title": None,
        "concepts": ["folk art", "American scenes"],
        "themes": ["nighttime", "baseball"],
    },
    {
        "match": ("thomas moran", "moran"),
        "artist": "Thomas Moran",
        "title": None,
        "concepts": ["Manifest Destiny", "Hudson River School"],
        "themes": ["western landscape"],
    },
    {
        "match": ("sanford biggers", "biggers"),
        "artist": "Sanford Biggers",
        "title": "Reclining Liberty",
        "concepts": ["liberty", "Brooklyn Waterfront"],
        "themes": ["contemporary sculpture"],
    },
    {
        "match": ("alexis rockman", "rockman"),
        "artist": "Alexis Rockman",
        "title": "Manifest Destiny",
        "concepts": ["Manifest Destiny", "ecological futures"],
        "themes": ["apocalyptic landscape"],
    },
    {
        "match": ("sam gilliam", "gilliam"),
        "artist": "Sam Gilliam",
        "title": None,
        "concepts": ["Color Field", "draped canvas"],
        "themes": ["abstraction", "installation"],
    },
    {
        "match": ("leonardo drew", "drew"),
        "artist": "Leonardo Drew",
        "title": None,
        "concepts": ["found objects", "materiality"],
        "themes": ["assemblage"],
    },
]

_CONCEPT_KEYWORDS = ("manifest destiny", "found objects", "draped canvas", "brooklyn waterfront")


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


def _infer_title(block: str, hint: dict | None) -> str | None:
    if hint and hint.get("title"):
        return hint["title"]

    quoted = re.search(r'"([^"]+)"|“([^”]+)”|‘([^’]+)’', block)
    if quoted:
        return next(group for group in quoted.groups() if group)

    if hint:
        for theme in hint.get("themes", []):
            if theme.lower() in block.lower():
                return None

    return None


def _themes_from_block(block: str, hint: dict | None) -> list[str]:
    themes = list(hint.get("themes", [])) if hint else []
    for keyword in _CONCEPT_KEYWORDS:
        if keyword in block.lower() and keyword.title() not in themes:
            themes.append(keyword.title())
    return themes


def _concepts_from_block(block: str, hint: dict | None) -> list[str]:
    concepts = list(hint.get("concepts", [])) if hint else []
    lowered = block.lower()
    if "manifest destiny" in lowered and "Manifest Destiny" not in concepts:
        concepts.append("Manifest Destiny")
    if "found object" in lowered and "found objects" not in [c.lower() for c in concepts]:
        concepts.append("found objects")
    if "draped canvas" in lowered and "draped canvas" not in [c.lower() for c in concepts]:
        concepts.append("draped canvas")
    if "brooklyn waterfront" in lowered and "Brooklyn Waterfront" not in concepts:
        concepts.append("Brooklyn Waterfront")
    return concepts


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


def _concept_links_from_artworks(artworks: list[ArtworkImportDraft]) -> list[ConceptLinkDraft]:
    links: list[ConceptLinkDraft] = []
    seen: set[tuple[str, str]] = set()

    for artwork in artworks:
        source = artwork.artist or artwork.title
        if not source:
            continue
        for concept in artwork.concepts:
            key = (source, concept)
            if key in seen:
                continue
            seen.add(key)
            links.append(
                ConceptLinkDraft(source=source, target=concept, relationship="context")
            )

    return links


class MockMuseumNotesImportProvider:
    async def extract(self, request: MuseumNotesImportRequest) -> MuseumNotesImportResponse:
        blocks = _split_note_blocks(request.text)
        artworks: list[ArtworkImportDraft] = []

        for block in blocks:
            hint = _match_artist_hint(block)
            artist = hint["artist"] if hint else None
            concepts = _concepts_from_block(block, hint)
            themes = _themes_from_block(block, hint)
            title = _infer_title(block, hint)

            if not hint and len(block.split()) < 4:
                continue

            artworks.append(
                ArtworkImportDraft(
                    title=title,
                    artist=artist,
                    period_or_year=None,
                    medium=None,
                    notes=block,
                    themes=themes,
                    concepts=concepts,
                    suggested_annotations=_suggested_annotations_for_block(block, concepts),
                )
            )

        if not artworks and request.text.strip():
            artworks.append(
                ArtworkImportDraft(
                    title=None,
                    artist=None,
                    notes=request.text.strip(),
                    suggested_annotations=[
                        SuggestedAnnotationDraft(
                            category=AnnotationCategory.observation,
                            note="Review pasted notes and identify individual artworks.",
                        )
                    ],
                )
            )

        summary_parts = [
            f"Imported notebook entries for {request.default_museum}.",
            f"{len(artworks)} artwork{'s' if len(artworks) != 1 else ''} extracted from pasted notes.",
        ]
        if artworks and artworks[0].concepts:
            summary_parts.append(f"Themes include {', '.join(artworks[0].concepts[:3])}.")

        visit = VisitImportDraft(
            museum_name=request.default_museum,
            city=request.default_city,
            visit_date=_default_visit_date(request),
            summary=" ".join(summary_parts),
        )

        concept_links = _concept_links_from_artworks(artworks)

        return MuseumNotesImportResponse(
            visit=visit,
            artworks=artworks,
            concept_links=concept_links,
            source="mock",
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

        text_blocks = [
            block.text for block in message.content if getattr(block, "type", None) == "text"
        ]
        if not text_blocks:
            raise ResearchProviderError("Claude returned an empty response.")

        try:
            parsed = _ClaudeImportPayload.model_validate(_extract_json(text_blocks[0]))
        except ValidationError as exc:
            raise ResearchProviderError(
                "Claude response did not match the expected museum notes import schema."
            ) from exc

        return MuseumNotesImportResponse(
            visit=parsed.visit,
            artworks=parsed.artworks,
            concept_links=parsed.concept_links,
            source="claude",
        )


def get_museum_notes_import_provider() -> MuseumNotesImportProvider:
    api_key = settings.anthropic_api_key
    if not api_key or not api_key.strip():
        return MockMuseumNotesImportProvider()

    return ClaudeMuseumNotesImportProvider(api_key)
