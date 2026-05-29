from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin_user
from app.database import get_db
from app.models import Artwork
from app.schemas import ArtworkEnrichmentRead
from app.services.artwork_enrichment import (
    latest_research_draft,
    parse_enrichment_payload,
    request_artwork_enrichment,
    resolve_enrichment_identification,
)

router = APIRouter(prefix="/artworks", tags=["enrichment"])


def _get_artwork_or_404(db: Session, artwork_id: int) -> Artwork:
    artwork = db.get(Artwork, artwork_id)
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")
    return artwork


def _enrichment_read(artwork: Artwork, db: Session) -> ArtworkEnrichmentRead:
    draft, note_id = latest_research_draft(db, artwork.id)
    lookup, identification, visual_analysis = parse_enrichment_payload(artwork.enrichment_lookup)
    identification = resolve_enrichment_identification(artwork, draft, identification)
    if visual_analysis is None and draft and draft.visual_analysis:
        visual_analysis = draft.visual_analysis

    return ArtworkEnrichmentRead(
        status=artwork.enrichment_status,  # type: ignore[arg-type]
        stage=artwork.enrichment_stage,  # type: ignore[arg-type]
        error=artwork.enrichment_error,
        research_note_id=note_id,
        draft=draft,
        lookup=lookup,
        identification=identification,
        visual_analysis=visual_analysis,
    )


@router.get("/{artwork_id}/enrichment", response_model=ArtworkEnrichmentRead)
def get_artwork_enrichment(artwork_id: int, db: Session = Depends(get_db)) -> ArtworkEnrichmentRead:
    artwork = _get_artwork_or_404(db, artwork_id)
    return _enrichment_read(artwork, db)


@router.post(
    "/{artwork_id}/enrichment",
    response_model=ArtworkEnrichmentRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_artwork_enrichment(
    artwork_id: int,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
    broaden_search: bool = Query(default=False),
    exact_artwork: bool = Query(default=False),
) -> ArtworkEnrichmentRead:
    artwork = _get_artwork_or_404(db, artwork_id)
    if not artwork.image_url:
        raise HTTPException(
            status_code=400,
            detail="Upload a photo before running AI enrichment.",
        )

    request_artwork_enrichment(
        db,
        artwork,
        broaden_search=broaden_search,
        exact_artwork_search=exact_artwork,
        force=True,
    )
    db.refresh(artwork)

    return ArtworkEnrichmentRead(
        status=artwork.enrichment_status,  # type: ignore[arg-type]
        stage=artwork.enrichment_stage,
        error=artwork.enrichment_error,
        research_note_id=None,
        draft=None,
        lookup=None,
        identification=None,
        visual_analysis=None,
    )
