"""Remove accidental pytest records from a development database."""

from __future__ import annotations

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.models import Annotation, Artwork, CulturalEntity, ResearchNote, Visit

# Visits created by backend integration tests (museum_name).
TEST_VISIT_MUSEUM_NAMES: frozenset[str] = frozenset(
    {
        "Test Museum",
        "Delete Museum",
        "Unplaced Annotation Museum",
        "Partial Coordinate Museum",
        "Edit Museum",
        "Move Pin Museum",
        "Bulk Delete Museum",
        "Admin Dashboard Museum",
        "Unique Admin Search Museum",
    }
)

# Orphan / API-only test artworks (no visit or generic titles).
TEST_ARTWORK_TITLES: frozenset[str] = frozenset(
    {
        "Coordinate test",
        "Unplaced artwork",
        "Editable artwork",
        "Move pin artwork",
        "Delete annotation artwork",
        "Partial coordinate artwork",
        "Accept flow artwork",
        "Suggestion status artwork",
        "Infer accepted artwork",
        "Missing artwork",
        "Research artwork",
        "Test artwork",
        "Untitled",
        "Unknown",
    }
)

TEST_VISIT_NOTES: frozenset[str] = frozenset({"Admin CRUD visit"})


def _artwork_ids_for_visits(db: Session, visit_ids: list[int]) -> list[int]:
    if not visit_ids:
        return []
    rows = db.scalars(select(Artwork.id).where(Artwork.visit_id.in_(visit_ids))).all()
    return list(rows)


def _delete_artwork_graph(db: Session, artwork_ids: list[int]) -> None:
    if not artwork_ids:
        return
    db.execute(delete(Annotation).where(Annotation.artwork_id.in_(artwork_ids)))
    db.execute(delete(ResearchNote).where(ResearchNote.artwork_id.in_(artwork_ids)))
    db.execute(delete(Artwork).where(Artwork.id.in_(artwork_ids)))


def cleanup_test_data(db: Session) -> dict[str, int]:
    """Delete known pytest fixtures from the given database session."""
    visit_ids = list(
        db.scalars(
            select(Visit.id).where(
                or_(
                    Visit.museum_name.in_(TEST_VISIT_MUSEUM_NAMES),
                    Visit.notes.in_(TEST_VISIT_NOTES),
                )
            )
        ).all()
    )

    artwork_ids = _artwork_ids_for_visits(db, visit_ids)
    orphan_artwork_ids = list(
        db.scalars(select(Artwork.id).where(Artwork.title.in_(TEST_ARTWORK_TITLES))).all()
    )
    artwork_ids = list(dict.fromkeys([*artwork_ids, *orphan_artwork_ids]))

    _delete_artwork_graph(db, artwork_ids)

    if visit_ids:
        db.execute(delete(CulturalEntity).where(CulturalEntity.visit_id.in_(visit_ids)))
        db.execute(delete(Visit).where(Visit.id.in_(visit_ids)))

    db.commit()

    return {
        "visits_deleted": len(visit_ids),
        "artworks_deleted": len(artwork_ids),
    }
