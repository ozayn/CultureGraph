from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


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
    x_percent: float = Field(ge=0, le=100)
    y_percent: float = Field(ge=0, le=100)
    category: AnnotationCategory
    text: str = Field(min_length=1)


class AnnotationCreate(AnnotationBase):
    pass


class AnnotationUpdate(BaseModel):
    x_percent: float | None = Field(default=None, ge=0, le=100)
    y_percent: float | None = Field(default=None, ge=0, le=100)
    category: AnnotationCategory | None = None
    text: str | None = Field(default=None, min_length=1)


class AnnotationRead(AnnotationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    artwork_id: int
    created_at: datetime


class ResearchDraft(BaseModel):
    short_summary: str
    historical_context: str
    visual_elements_to_notice: list[str]
    related_questions: list[str]
    suggested_annotations: list[dict[str, str]]
    possible_title: str | None = None
    possible_artist: str | None = None
    period_or_movement: str | None = None
    ocr_label_text: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source: str = "mock"


class ClaudeSuggestedAnnotation(BaseModel):
    category: AnnotationCategory
    text: str = Field(min_length=1)


class ClaudeResearchResponse(BaseModel):
    possible_title: str | None = None
    possible_artist: str | None = None
    period_or_movement: str | None = None
    visible_elements: list[str] = Field(min_length=1)
    ocr_label_text: str | None = None
    historical_context: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    suggested_annotations: list[ClaudeSuggestedAnnotation] = Field(min_length=1)


class ResearchNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    artwork_id: int
    short_summary: str
    historical_context: str
    visual_elements_to_notice: str
    related_questions: str
    suggested_annotations: str
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
    object_url: str | None = None
    accession_number: str | None = None
    source_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    rights_label: str | None = None
    external_id: str | None = None


class ArtworkLookupResponse(BaseModel):
    candidates: list[ArtworkLookupCandidateRead]
    sources_searched: list[str]
    disclaimer: str = (
        "Matches are suggestions from open museum collection data. "
        "Review title, artist, and image before applying."
    )
