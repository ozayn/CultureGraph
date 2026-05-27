from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import AnnotationCategory, CulturalEntityType


class AdminSummaryRead(BaseModel):
    visits: int
    artworks: int
    annotations: int
    cultural_entities: int
    research_notes: int


class AdminListMeta(BaseModel):
    total: int
    limit: int
    offset: int
    search: str | None = None


class AdminVisitRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    museum_name: str
    city: str
    visit_date: date
    notes: str | None
    created_at: datetime


class AdminArtworkRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    visit_id: int | None
    title: str | None
    artist: str | None
    year_period: str | None
    image_url: str | None
    image_thumbnail_url: str | None
    catalog_source: str | None
    created_at: datetime


class AdminAnnotationRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    artwork_id: int
    category: AnnotationCategory
    text: str
    x_percent: float | None
    y_percent: float | None
    created_at: datetime


class AdminEntityRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    visit_id: int
    entity_type: CulturalEntityType
    name: str
    description: str | None
    image_url: str | None
    thumbnail_url: str | None
    created_at: datetime


class AdminResearchNoteRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    artwork_id: int
    short_summary: str
    created_at: datetime


class AdminVisitListResponse(BaseModel):
    records: list[AdminVisitRecord]
    meta: AdminListMeta


class AdminArtworkListResponse(BaseModel):
    records: list[AdminArtworkRecord]
    meta: AdminListMeta


class AdminAnnotationListResponse(BaseModel):
    records: list[AdminAnnotationRecord]
    meta: AdminListMeta


class AdminEntityListResponse(BaseModel):
    records: list[AdminEntityRecord]
    meta: AdminListMeta


class AdminResearchNoteListResponse(BaseModel):
    records: list[AdminResearchNoteRecord]
    meta: AdminListMeta


class AdminBulkDeleteRequest(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=200)


class AdminBulkDeleteResponse(BaseModel):
    deleted_count: int
