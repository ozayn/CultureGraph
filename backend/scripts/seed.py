"""Seed sample museum visits and artworks."""

import asyncio
from datetime import date

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Annotation, AnnotationCategory, Artwork, ResearchNote, Visit
from app.services.research import MockLLMProvider, serialize_research_draft


def seed(db: Session) -> None:
    if db.query(Visit).count() > 0:
        print("Database already seeded, skipping.")
        return

    visit = Visit(
        museum_name="Metropolitan Museum of Art",
        city="New York",
        visit_date=date(2026, 3, 15),
        notes="Focused on European paintings wing.",
    )
    db.add(visit)
    db.flush()

    artwork = Artwork(
        visit_id=visit.id,
        title="The Harvesters",
        artist="Pieter Bruegel the Elder",
        year_period="1565",
        medium="Oil on wood",
        museum_gallery="Metropolitan Museum of Art",
        personal_notes="Struck by the golden afternoon light and distant landscape.",
    )
    db.add(artwork)
    db.flush()

    db.add_all(
        [
            Annotation(
                artwork_id=artwork.id,
                x_percent=42.0,
                y_percent=35.0,
                category=AnnotationCategory.composition,
                text="Central grouping of harvesters creates a rhythmic diagonal.",
            ),
            Annotation(
                artwork_id=artwork.id,
                x_percent=68.0,
                y_percent=22.0,
                category=AnnotationCategory.observation,
                text="Tiny figures in the far distance suggest scale and daily labor.",
            ),
        ]
    )

    provider = MockLLMProvider()

    draft = asyncio.run(
        provider.generate_research(
            {
                "title": artwork.title,
                "artist": artwork.artist,
                "year_period": artwork.year_period,
            }
        )
    )
    db.add(ResearchNote(artwork_id=artwork.id, **serialize_research_draft(draft)))

    db.add(
        Artwork(
            title="Study for a Portrait",
            artist="Unknown",
            year_period="c. 1880",
            medium="Charcoal on paper",
            museum_gallery="Sketchbook",
            personal_notes="Placeholder entry without visit link.",
        )
    )

    db.commit()
    print("Seed data created.")


if __name__ == "__main__":
    session = SessionLocal()
    try:
        seed(session)
    finally:
        session.close()
