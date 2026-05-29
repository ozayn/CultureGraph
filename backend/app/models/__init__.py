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
    enrichment_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="idle", server_default="idle"
    )
    enrichment_stage: Mapped[str | None] = mapped_column(String(64))
    enrichment_error: Mapped[str | None] = mapped_column(Text)
    enrichment_lookup: Mapped[dict | list | None] = mapped_column(JSON)
    label_image_url: Mapped[str | None] = mapped_column(String(512))
    label_image_thumbnail_url: Mapped[str | None] = mapped_column(String(512))
    label_ocr_text: Mapped[str | None] = mapped_column(Text)
    label_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
    period_or_movement: Mapped[str | None] = mapped_column(String(255))
    ocr_label_text: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    visual_analysis: Mapped[str | None] = mapped_column(Text)
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


class CollectionArtwork(Base):
    __tablename__ = "collection_artworks"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_object_id: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    artist: Mapped[str | None] = mapped_column(String(512))
    date: Mapped[str | None] = mapped_column(String(128))
    medium: Mapped[str | None] = mapped_column(String(512))
    image_url: Mapped[str | None] = mapped_column(String(1024))
    thumbnail_url: Mapped[str | None] = mapped_column(String(1024))
    object_url: Mapped[str | None] = mapped_column(String(1024))
    rights_label: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    embeddings: Mapped[list["CollectionImageEmbedding"]] = relationship(
        back_populates="collection_artwork",
        cascade="all, delete-orphan",
    )


class CollectionImageEmbedding(Base):
    __tablename__ = "collection_image_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_artwork_id: Mapped[int] = mapped_column(
        ForeignKey("collection_artworks.id", ondelete="CASCADE"),
        nullable=False,
    )
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding_vector: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    collection_artwork: Mapped["CollectionArtwork"] = relationship(back_populates="embeddings")


class AudioNote(Base):
    __tablename__ = "audio_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    visit_id: Mapped[int | None] = mapped_column(ForeignKey("visits.id", ondelete="CASCADE"))
    artwork_id: Mapped[int | None] = mapped_column(ForeignKey("artworks.id", ondelete="CASCADE"))
    audio_url: Mapped[str] = mapped_column(String(512), nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    transcript: Mapped[str | None] = mapped_column(Text)
    cleaned_note: Mapped[str | None] = mapped_column(Text)
    interpretation_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    visit: Mapped["Visit | None"] = relationship()
    artwork: Mapped["Artwork | None"] = relationship()
