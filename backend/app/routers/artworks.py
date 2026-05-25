import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin_user

from app.database import get_db
from app.models import Artwork, Visit
from app.schemas import (
    ArtworkCreate,
    ArtworkLookupCandidateRead,
    ArtworkLookupResponse,
    ArtworkRead,
    ArtworkUpdate,
)
from app.services.artwork_lookup import lookup_artwork_candidates
from app.services.image_upload import (
    process_and_store_artwork_image,
    read_upload_with_limit,
    remove_artwork_image_files,
)
from app.services.record_cleanup import delete_artwork as delete_artwork_record
from app.sources.base import ArtworkLookupQuery
from app.sources.nga import NGA_SOURCE_NAME, is_nga_museum, should_search_nga

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/artworks", tags=["artworks"])


def _get_artwork_or_404(db: Session, artwork_id: int) -> Artwork:
    artwork = db.get(Artwork, artwork_id)
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")
    return artwork


@router.get("", response_model=list[ArtworkRead])
def list_artworks(visit_id: int | None = None, db: Session = Depends(get_db)) -> list[Artwork]:
    query = db.query(Artwork)
    if visit_id is not None:
        query = query.filter(Artwork.visit_id == visit_id)
    return query.order_by(Artwork.created_at.desc()).all()


@router.post("", response_model=ArtworkRead, status_code=status.HTTP_201_CREATED)
def create_artwork(
    payload: ArtworkCreate,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
) -> Artwork:
    if payload.visit_id is not None and not db.get(Visit, payload.visit_id):
        raise HTTPException(status_code=400, detail="Visit not found")

    artwork = Artwork(**payload.model_dump())
    db.add(artwork)
    db.commit()
    db.refresh(artwork)
    return artwork


@router.get("/{artwork_id}", response_model=ArtworkRead)
def get_artwork(artwork_id: int, db: Session = Depends(get_db)) -> Artwork:
    return _get_artwork_or_404(db, artwork_id)


@router.get("/{artwork_id}/lookup-image", response_model=ArtworkLookupResponse)
def lookup_artwork_image(
    artwork_id: int,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
    source: str | None = Query(default=None, description="Explicit source, e.g. nga"),
) -> ArtworkLookupResponse:
    artwork = _get_artwork_or_404(db, artwork_id)
    museum_name = artwork.visit.museum_name if artwork.visit else None

    if source is None and museum_name and not is_nga_museum(museum_name):
        return ArtworkLookupResponse(candidates=[], sources_searched=[])

    query = ArtworkLookupQuery(
        title=artwork.title,
        artist=artwork.artist,
        museum_name=museum_name,
        year_period=artwork.year_period,
        notes=artwork.personal_notes,
        source=source,
    )
    candidates = lookup_artwork_candidates(query)
    sources_searched = [NGA_SOURCE_NAME] if should_search_nga(query) else []

    return ArtworkLookupResponse(
        candidates=[
            ArtworkLookupCandidateRead.model_validate(item, from_attributes=True)
            for item in candidates
        ],
        sources_searched=sources_searched,
    )


@router.put("/{artwork_id}", response_model=ArtworkRead)
@router.patch("/{artwork_id}", response_model=ArtworkRead)
def update_artwork(
    artwork_id: int,
    payload: ArtworkUpdate,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
) -> Artwork:
    artwork = _get_artwork_or_404(db, artwork_id)

    data = payload.model_dump(exclude_unset=True)
    if "visit_id" in data and data["visit_id"] is not None:
        if not db.get(Visit, data["visit_id"]):
            raise HTTPException(status_code=400, detail="Visit not found")

    for key, value in data.items():
        setattr(artwork, key, value)

    db.commit()
    db.refresh(artwork)
    return artwork


@router.delete("/{artwork_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_artwork(
    artwork_id: int,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
) -> None:
    artwork = _get_artwork_or_404(db, artwork_id)
    delete_artwork_record(db, artwork)
    db.commit()


@router.post("/{artwork_id}/image", response_model=ArtworkRead)
async def upload_artwork_image(
    artwork_id: int,
    user: Annotated[dict[str, str], Depends(require_admin_user)],
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Artwork:
    artwork = _get_artwork_or_404(db, artwork_id)
    logger.info(
        "artwork image upload requested artwork_id=%s user=%s content_type=%s",
        artwork_id,
        user.get("email"),
        file.content_type,
    )

    remove_artwork_image_files(
        image_url=artwork.image_url,
        image_thumbnail_url=artwork.image_thumbnail_url,
    )

    data = await read_upload_with_limit(file)
    saved = process_and_store_artwork_image(
        artwork_id=artwork_id,
        data=data,
        filename=file.filename,
        content_type=file.content_type,
    )

    artwork.image_url = saved.image_url
    artwork.image_thumbnail_url = saved.image_thumbnail_url
    artwork.image_width = saved.image_width
    artwork.image_height = saved.image_height
    artwork.image_mime_type = saved.image_mime_type
    artwork.image_file_size = saved.image_file_size
    artwork.captured_at = saved.captured_at
    artwork.captured_date_source = saved.captured_date_source
    db.commit()
    db.refresh(artwork)

    logger.info(
        "artwork image stored artwork_id=%s url=%s bytes=%s",
        artwork_id,
        saved.image_url,
        saved.image_file_size,
    )
    return artwork
