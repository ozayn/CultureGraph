from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin_user

from app.database import get_db
from app.models import Artwork, ResearchNote
from app.schemas import ResearchDraft, ResearchNoteRead
from app.services.research import (
    ResearchConfigurationError,
    ResearchProviderError,
    get_research_provider,
    serialize_research_draft,
)

router = APIRouter(prefix="/artworks", tags=["research"])


@router.post("/{artwork_id}/research", response_model=ResearchDraft)
async def generate_research(
    artwork_id: int,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
) -> ResearchDraft:
    artwork = db.get(Artwork, artwork_id)
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")

    context = {
        "title": artwork.title,
        "artist": artwork.artist,
        "year_period": artwork.year_period,
        "medium": artwork.medium,
        "museum_gallery": artwork.museum_gallery,
        "personal_notes": artwork.personal_notes,
        "image_url": artwork.image_url,
    }

    provider = get_research_provider()

    try:
        draft = await provider.generate_research(context)
    except ResearchConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ResearchProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

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


@router.delete(
    "/{artwork_id}/research/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_research_note(
    artwork_id: int,
    note_id: int,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
) -> None:
    artwork = db.get(Artwork, artwork_id)
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")

    note = db.get(ResearchNote, note_id)
    if not note or note.artwork_id != artwork_id:
        raise HTTPException(status_code=404, detail="Research note not found")

    db.delete(note)
    db.commit()
