import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AnnotationCategory(str, enum.Enum):
    observation = "observation"
    symbol = "symbol"
    history = "history"
    question = "question"
    composition = "composition"
    material = "material"


class CulturalEntityType(str, enum.Enum):
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


class Visit(Base):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(primary_key=True)
    museum_name: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(255), nullable=False)
    visit_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    artworks: Mapped[list["Artwork"]] = relationship(back_populates="visit")
    cultural_entities: Mapped[list["CulturalEntity"]] = relationship(
        back_populates="visit", cascade="all, delete-orphan"
    )


class Artwork(Base):
    __tablename__ = "artworks"

    id: Mapped[int] = mapped_column(primary_key=True)
    visit_id: Mapped[int | None] = mapped_column(ForeignKey("visits.id"), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    artist: Mapped[str | None] = mapped_column(String(255))
    year_period: Mapped[str | None] = mapped_column(String(100))
    medium: Mapped[str | None] = mapped_column(String(255))
    museum_gallery: Mapped[str | None] = mapped_column(String(255))
    image_url: Mapped[str | None] = mapped_column(String(512))
    image_master_url: Mapped[str | None] = mapped_column(String(512))
    image_thumbnail_url: Mapped[str | None] = mapped_column(String(512))
    crop_x_percent: Mapped[float | None] = mapped_column()
    crop_y_percent: Mapped[float | None] = mapped_column()
    crop_width_percent: Mapped[float | None] = mapped_column()
    crop_height_percent: Mapped[float | None] = mapped_column()
    image_width: Mapped[int | None] = mapped_column()
    image_height: Mapped[int | None] = mapped_column()
    image_mime_type: Mapped[str | None] = mapped_column(String(64))
    image_file_size: Mapped[int | None] = mapped_column()
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_date_source: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    catalog_source: Mapped[str | None] = mapped_column(String(128))
    catalog_image_url: Mapped[str | None] = mapped_column(String(512))
    catalog_thumbnail_url: Mapped[str | None] = mapped_column(String(512))
    catalog_object_url: Mapped[str | None] = mapped_column(String(512))
    catalog_accession_number: Mapped[str | None] = mapped_column(String(64))
    catalog_rights_label: Mapped[str | None] = mapped_column(String(255))
    personal_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    visit: Mapped["Visit | None"] = relationship(back_populates="artworks")
    annotations: Mapped[list["Annotation"]] = relationship(
        back_populates="artwork", cascade="all, delete-orphan"
    )
    research_notes: Mapped[list["ResearchNote"]] = relationship(
        back_populates="artwork", cascade="all, delete-orphan"
    )


class Annotation(Base):
    __tablename__ = "annotations"

    id: Mapped[int] = mapped_column(primary_key=True)
    artwork_id: Mapped[int] = mapped_column(ForeignKey("artworks.id"), nullable=False)
    x_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    y_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    category: Mapped[AnnotationCategory] = mapped_column(
        Enum(AnnotationCategory, name="annotation_category"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    linked_entity_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    linked_concept_names: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    artwork: Mapped["Artwork"] = relationship(back_populates="annotations")


class ResearchNote(Base):
    __tablename__ = "research_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    artwork_id: Mapped[int] = mapped_column(ForeignKey("artworks.id"), nullable=False)
    short_summary: Mapped[str] = mapped_column(Text, nullable=False)
    historical_context: Mapped[str] = mapped_column(Text, nullable=False)
    visual_elements_to_notice: Mapped[str] = mapped_column(Text, nullable=False)
    related_questions: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_annotations: Mapped[str] = mapped_column(Text, nullable=False)
    possible_title: Mapped[str | None] = mapped_column(String(255))
    possible_artist: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    artwork: Mapped["Artwork"] = relationship(back_populates="research_notes")


class CulturalEntity(Base):
    __tablename__ = "cultural_entities"

    id: Mapped[int] = mapped_column(primary_key=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("visits.id"), nullable=False)
    entity_type: Mapped[CulturalEntityType] = mapped_column(
        Enum(CulturalEntityType, name="cultural_entity_type"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    themes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    concepts: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    movements: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    historical_events: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    related_entities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    image_url: Mapped[str | None] = mapped_column(String(512))
    thumbnail_url: Mapped[str | None] = mapped_column(String(512))
    image_source_name: Mapped[str | None] = mapped_column(String(128))
    image_source_url: Mapped[str | None] = mapped_column(String(512))
    image_rights_label: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    visit: Mapped["Visit"] = relationship(back_populates="cultural_entities")
