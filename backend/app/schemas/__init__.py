from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


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
