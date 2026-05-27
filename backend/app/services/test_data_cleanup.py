"""Remove accidental pytest records from a development database."""

from __future__ import annotations

from datetime import date

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
        "NGA",
    }
)

# Real museum names used as fixtures in HTTP/integration tests.
TEST_FIXTURE_MUSEUM_NAMES: frozenset[str] = frozenset(
    {
        "National Gallery of Art",
        "Smithsonian American Art Museum",
        "The Met",
    }
)

# Pytest commonly uses these calendar days across visit fixtures.
TEST_FIXTURE_VISIT_DATES: frozenset[date] = frozenset(
    {
        date(2026, 5, 23),
        date(2026, 5, 24),
        date(2026, 5, 25),
    }
)

TEST_VISIT_NOTES: frozenset[str] = frozenset(
    {
        "Admin CRUD visit",
        "Annotation test visit",
    }
)

TEST_VISIT_NOTE_PREFIXES: tuple[str, ...] = (
    "Imported notebook entries for Smithsonian",
)

# Orphan / API-only test artworks and titles attached to polluted visits.
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
        "Upload test",
        "EXIF upload",
        "Bad upload",
        "Large upload",
        "Static file test",
        "Region test",
        "Some artwork",
        "Four Dancers",
        "George Washington",
        "The Adoration of the Magi",
        "Western landscape",
        "Plain annotation",
        "Update tags",
        "Unauthorized edit",
        "Bulk Delete Artwork",
        "Bulk Delete Artwork Only",
        "ZZZ Nonexistent Artwork XYZ",
        "Grandma Moses",
        "Sam Gilliam",
        "Study for a Portrait",
        "The Grand Canyon of the Yellowstone",
    }
)

TEST_ARTWORK_ARTISTS: frozenset[str] = frozenset(
    {
        "Test artist",
        "ZZZZZZ Nobody Known",
    }
)

# Dev seed data — never delete during cleanup.
DEV_SEED_MUSEUM_NAMES: frozenset[str] = frozenset({"Metropolitan Museum of Art"})


def _note_is_test(notes: str | None) -> bool:
    if not notes:
        return False
    if notes in TEST_VISIT_NOTES:
        return True
    return any(notes.startswith(prefix) for prefix in TEST_VISIT_NOTE_PREFIXES)


def _visit_is_test_fixture(visit: Visit) -> bool:
    if visit.museum_name in DEV_SEED_MUSEUM_NAMES:
        return False
    if visit.museum_name in TEST_VISIT_MUSEUM_NAMES:
        return True
    if _note_is_test(visit.notes):
        return True
    if (
        visit.museum_name in TEST_FIXTURE_MUSEUM_NAMES
        and visit.visit_date in TEST_FIXTURE_VISIT_DATES
    ):
        return True
    return False


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


def _collect_polluted_visit_ids(db: Session) -> list[int]:
    visit_ids: set[int] = set()

    for visit in db.scalars(select(Visit)).all():
        if _visit_is_test_fixture(visit):
            visit_ids.add(visit.id)

    visit_ids.update(
        db.scalars(
            select(Artwork.visit_id).where(
                Artwork.visit_id.is_not(None),
                or_(
                    Artwork.title.in_(TEST_ARTWORK_TITLES),
                    Artwork.artist.in_(TEST_ARTWORK_ARTISTS),
                ),
            )
        ).all()
    )

    return sorted(visit_ids)


def cleanup_test_data(db: Session) -> dict[str, int]:
    """Delete known pytest fixtures from the given database session."""
    visit_ids = _collect_polluted_visit_ids(db)

    artwork_ids = _artwork_ids_for_visits(db, visit_ids)
    orphan_artwork_ids = list(
        db.scalars(
            select(Artwork.id).where(
                or_(
                    Artwork.title.in_(TEST_ARTWORK_TITLES),
                    Artwork.artist.in_(TEST_ARTWORK_ARTISTS),
                    (
                        Artwork.visit_id.is_(None)
                        & Artwork.title.is_(None)
                        & Artwork.artist.is_(None)
                    ),
                )
            )
        ).all()
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
