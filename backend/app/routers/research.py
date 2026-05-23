from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Artwork, ResearchNote
from app.schemas import ResearchDraft, ResearchNoteRead
from app.services.research import llm_provider, serialize_research_draft

router = APIRouter(prefix="/artworks", tags=["research"])


@router.post("/{artwork_id}/research", response_model=ResearchDraft)
async def generate_research(artwork_id: int, db: Session = Depends(get_db)) -> ResearchDraft:
    artwork = db.get(Artwork, artwork_id)
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")

    context = {
        "title": artwork.title,
        "artist": artwork.artist,
        "year_period": artwork.year_period,
        "medium": artwork.medium,
        "museum_gallery": artwork.museum_gallery,
    }

    draft = await llm_provider.generate_research(context)
    serialized = serialize_research_draft(draft)

    note = ResearchNote(artwork_id=artwork_id, **serialized)
    db.add(note)
    db.commit()

    return draft


@router.get("/{artwork_id}/research", response_model=list[ResearchNoteRead])
def list_research_notes(artwork_id: int, db: Session = Depends(get_db)) -> list[ResearchNote]:
    artwork = db.get(Artwork, artwork_id)
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")

    return (
        db.query(ResearchNote)
        .filter(ResearchNote.artwork_id == artwork_id)
        .order_by(ResearchNote.created_at.desc())
        .all()
    )
