from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CulturalEntityType(str, Enum):
    artwork = "artwork"
    artist = "artist"
    concept = "concept"
    movement = "movement"
    technique = "technique"
    material = "material"
    historical_event = "historical_event"
    symbol = "symbol"
    architecture = "architecture"
    museum_space = "museum_space"
    political_idea = "political_idea"


class AnnotationCategory(str, Enum):
    observation = "observation"
    symbol = "symbol"
    history = "history"
    question = "question"
    composition = "composition"
    material = "material"


class VisitBase(BaseModel):
    museum_name: str = Field(min_length=1, max_length=255)
    city: str = Field(min_length=1, max_length=255)
    visit_date: date
    notes: str | None = None


class VisitCreate(VisitBase):
    pass


class VisitUpdate(BaseModel):
    museum_name: str | None = Field(default=None, min_length=1, max_length=255)
    city: str | None = Field(default=None, min_length=1, max_length=255)
    visit_date: date | None = None
    notes: str | None = None


class VisitRead(VisitBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class CulturalEntityBase(BaseModel):
    entity_type: CulturalEntityType
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    themes: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    movements: list[str] = Field(default_factory=list)
    historical_events: list[str] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    image_url: str | None = None
    thumbnail_url: str | None = None
    image_source_name: str | None = None
    image_source_url: str | None = None
    image_rights_label: str | None = None
    visit_id: int


class CulturalEntityCreate(CulturalEntityBase):
    pass


class CulturalEntityRead(CulturalEntityBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class CulturalEntityUpdate(BaseModel):
    entity_type: CulturalEntityType | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    themes: list[str] | None = None
    concepts: list[str] | None = None
    movements: list[str] | None = None
    historical_events: list[str] | None = None
    related_entities: list[str] | None = None
    image_url: str | None = None
    thumbnail_url: str | None = None
    image_source_name: str | None = None
    image_source_url: str | None = None
    image_rights_label: str | None = None


class MuseumRead(BaseModel):
    name: str
    city: str
    neighborhood: str | None = None
    website: str | None = None
    type: str | None = None


class ArtworkBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    artist: str | None = None
    year_period: str | None = None
    medium: str | None = None
    museum_gallery: str | None = None
    image_url: str | None = None
    image_thumbnail_url: str | None = None
    image_width: int | None = None
    image_height: int | None = None
    image_mime_type: str | None = None
    image_file_size: int | None = None
    captured_at: datetime | None = None
    captured_date_source: str = "none"
    catalog_source: str | None = None
    catalog_object_url: str | None = None
    catalog_accession_number: str | None = None
    catalog_rights_label: str | None = None
    personal_notes: str | None = None
    visit_id: int | None = None


class ArtworkCreate(ArtworkBase):
    pass


class ArtworkUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    artist: str | None = None
    year_period: str | None = None
    medium: str | None = None
    museum_gallery: str | None = None
    image_url: str | None = None
    image_thumbnail_url: str | None = None
    catalog_source: str | None = None
    catalog_object_url: str | None = None
    catalog_accession_number: str | None = None
    catalog_rights_label: str | None = None
    personal_notes: str | None = None
    visit_id: int | None = None


class ArtworkRead(ArtworkBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class AnnotationBase(BaseModel):
    x_percent: float | None = Field(default=None, ge=0, le=100)
    y_percent: float | None = Field(default=None, ge=0, le=100)
    category: AnnotationCategory
    text: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    linked_entity_ids: list[int] = Field(default_factory=list)
    linked_concept_names: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_coordinate_pair(self) -> "AnnotationBase":
        if (self.x_percent is None) ^ (self.y_percent is None):
            raise ValueError("Both x_percent and y_percent must be set together or both omitted.")
        return self


class AnnotationCreate(AnnotationBase):
    pass


class AnnotationUpdate(BaseModel):
    x_percent: float | None = Field(default=None, ge=0, le=100)
    y_percent: float | None = Field(default=None, ge=0, le=100)
    category: AnnotationCategory | None = None
    text: str | None = Field(default=None, min_length=1)
    tags: list[str] | None = None
    linked_entity_ids: list[int] | None = None
    linked_concept_names: list[str] | None = None

    @model_validator(mode="after")
    def validate_coordinate_pair(self) -> "AnnotationUpdate":
        if (self.x_percent is None) ^ (self.y_percent is None):
            raise ValueError("Both x_percent and y_percent must be set together or both omitted.")
        return self


class AnnotationRead(AnnotationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    artwork_id: int
    created_at: datetime


class SuggestedAnnotationPosition(BaseModel):
    x_percent: float | None = Field(default=None, ge=0, le=100)
    y_percent: float | None = Field(default=None, ge=0, le=100)
    reason: str | None = None

    @model_validator(mode="after")
    def validate_coordinate_pair(self) -> "SuggestedAnnotationPosition":
        if (self.x_percent is None) ^ (self.y_percent is None):
            return SuggestedAnnotationPosition(
                x_percent=None,
                y_percent=None,
                reason=self.reason,
            )
        return self


class AiSuggestedAnnotation(BaseModel):
    category: AnnotationCategory
    note: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    linked_concept_names: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    suggested_position: SuggestedAnnotationPosition = Field(
        default_factory=SuggestedAnnotationPosition
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_payload(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        normalized = dict(data)
        if "note" not in normalized and "text" in normalized:
            normalized["note"] = normalized.pop("text")

        position = normalized.get("suggested_position")
        if not isinstance(position, dict):
            x_val = normalized.pop("x_percent", None)
            y_val = normalized.pop("y_percent", None)
            if x_val is not None or y_val is not None:
                normalized["suggested_position"] = {
                    "x_percent": x_val,
                    "y_percent": y_val,
                    "reason": normalized.pop("position_reason", None),
                }
        elif position.get("x_percent") is None or position.get("y_percent") is None:
            normalized["suggested_position"] = {
                **position,
                "x_percent": None,
                "y_percent": None,
            }

        normalized.setdefault("tags", [])
        normalized.setdefault("linked_concept_names", [])
        normalized.setdefault("confidence", 0.5)
        return normalized


class ResearchDraft(BaseModel):
    short_summary: str
    historical_context: str
    visual_elements_to_notice: list[str]
    related_questions: list[str]
    suggested_annotations: list[AiSuggestedAnnotation] = Field(default_factory=list)
    possible_title: str | None = None
    possible_artist: str | None = None
    period_or_movement: str | None = None
    ocr_label_text: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source: str = "mock"


class ClaudeSuggestedAnnotation(AiSuggestedAnnotation):
    pass


class ClaudeResearchResponse(BaseModel):
    possible_title: str | None = None
    possible_artist: str | None = None
    period_or_movement: str | None = None
    visible_elements: list[str] = Field(min_length=1)
    ocr_label_text: str | None = None
    historical_context: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    suggested_annotations: list[ClaudeSuggestedAnnotation] = Field(default_factory=list)


class ResearchNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    artwork_id: int
    short_summary: str
    historical_context: str
    visual_elements_to_notice: str
    related_questions: str
    suggested_annotations: str
    possible_title: str | None = None
    possible_artist: str | None = None
    period_or_movement: str | None = None
    created_at: datetime


class SuggestedAnnotationDraft(BaseModel):
    category: AnnotationCategory
    note: str = Field(min_length=1)


class ImportedEntityDraft(BaseModel):
    entity_type: CulturalEntityType
    name: str = Field(min_length=1)
    description: str | None = None
    related_entities: list[str] = Field(default_factory=list)
    uncertainty: str | None = None
    title: str | None = None
    artist: str | None = None
    period_or_year: str | None = None
    medium: str | None = None
    display_label: str | None = None
    themes: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    movements: list[str] = Field(default_factory=list)
    historical_events: list[str] = Field(default_factory=list)
    suggested_annotations: list[SuggestedAnnotationDraft] = Field(default_factory=list)
    image_url: str | None = None
    thumbnail_url: str | None = None
    image_source_name: str | None = None
    image_source_url: str | None = None
    image_rights_label: str | None = None


class ArtworkImportDraft(BaseModel):
    title: str | None = None
    artist: str | None = None
    period_or_year: str | None = None
    medium: str | None = None
    display_label: str | None = None
    notes: str | None = None
    themes: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    suggested_annotations: list[SuggestedAnnotationDraft] = Field(default_factory=list)


class VisitImportDraft(BaseModel):
    museum_name: str
    city: str
    visit_date: str
    summary: str


class ConceptLinkDraft(BaseModel):
    source: str
    target: str
    relationship: str


class MuseumNotesImportRequest(BaseModel):
    text: str = Field(min_length=1)
    default_museum: str = Field(default="Smithsonian American Art Museum", min_length=1)
    default_city: str = Field(default="Washington, DC", min_length=1)
    visit_date: date | None = None


class MuseumNotesImportResponse(BaseModel):
    visit: VisitImportDraft
    entities: list[ImportedEntityDraft]
    concept_links: list[ConceptLinkDraft] = Field(default_factory=list)
    source: str = "mock"
    ai_warning: str | None = None


class GoogleAuthRequest(BaseModel):
    id_token: str = Field(min_length=1)


class AuthUserRead(BaseModel):
    email: str
    name: str | None = None
    picture: str | None = None


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserRead


class ArtworkLookupCandidateRead(BaseModel):
    title: str
    artist: str | None = None
    date: str | None = None
    medium: str | None = None
    image_url: str | None = None
    image_thumbnail_url: str | None = None
    object_url: str | None = None
    accession_number: str | None = None
    source_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    rights_label: str | None = None
    external_id: str | None = None
    low_confidence: bool = False


class ArtworkLookupResponse(BaseModel):
    candidates: list[ArtworkLookupCandidateRead]
    sources_searched: list[str]
    query_used: str = ""
    query_source: Literal["ai_title", "saved_title", "artist_notes", "manual"] = "saved_title"
    alternate_title: str | None = None
    disclaimer: str = (
        "Matches are suggestions from open museum collection data. "
        "Review title, artist, and image before applying."
    )
    notice: str | None = None
