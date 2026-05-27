import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin_user

from app.database import get_db
from app.models import Artwork, Visit
from app.schemas import (
    ArtworkCreate,
    ArtworkImageRegionUpdate,
    ArtworkLookupCandidateRead,
    ArtworkLookupResponse,
    ArtworkRead,
    ArtworkUpdate,
)
from app.services.artwork_image_region import ArtworkImageRegion, regenerate_artwork_derivatives
from app.services.artwork_images import normalize_artwork_image_update
from app.services.artwork_lookup import lookup_artwork_candidates
from app.services.lookup_query import build_artwork_lookup_query
from app.sources.routing import (
    resolve_lookup_sources,
    sources_searched_labels,
)
from app.services.image_upload import (
    process_and_store_artwork_image,
    read_upload_with_limit,
    remove_artwork_image_files,
)
from app.services.record_cleanup import delete_artwork as delete_artwork_record
from app.sources.nga import should_search_nga
from app.sources.smithsonian import should_search_smithsonian

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
    source: str | None = Query(default=None, description="Explicit source, e.g. nga or all"),
    title_override: str | None = Query(default=None, description="Manual title search override"),
    artist_override: str | None = Query(default=None, description="Manual artist search override"),
    search_mode: str | None = Query(
        default=None,
        description="Force broader matching, e.g. broad",
    ),
    medium_type: str | None = Query(
        default=None,
        description="Filter by object type: 2d, 3d, or any",
    ),
    medium_override: str | None = Query(
        default=None,
        description="Override inferred artwork medium for ranking",
    ),
) -> ArtworkLookupResponse:
    artwork = _get_artwork_or_404(db, artwork_id)
    museum_name = artwork.visit.museum_name if artwork.visit else None

    built = build_artwork_lookup_query(
        artwork,
        db,
        museum_name=museum_name,
        title_override=title_override,
        artist_override=artist_override,
        source=source,
        medium_type=medium_type,
        medium_override=medium_override,
    )
    query = built.query

    if not resolve_lookup_sources(query):
        return ArtworkLookupResponse(
            candidates=[],
            sources_searched=[],
            query_used=built.query_used,
            query_source=built.query_source,
            alternate_title=built.alternate_title,
            expected_medium_type=built.expected_medium_type,
            medium_type_filter=built.medium_type_filter,
        )

    lookup_result = lookup_artwork_candidates(
        query,
        force_broad=(search_mode or "").strip().lower() == "broad",
    )
    candidates = lookup_result.candidates
    sources_searched = sources_searched_labels(query)

    notice: str | None = None
    if lookup_result.artist_fallback and candidates:
        artist_label = (query.artist or "").strip() or "this artist"
        notice = f"No exact title match found. Showing related works by {artist_label}."
    elif not candidates:
        if not built.query_used.strip():
            notice = "Add a title or artist to improve collection matching."
        elif should_search_smithsonian(query) and not should_search_nga(query):
            notice = "No close matches found in the Smithsonian Open Access index."
        elif should_search_nga(query) and not should_search_smithsonian(query):
            notice = "No close matches found in the National Gallery open collection index."
        else:
            notice = "No close matches found in the open collection indexes."

    return ArtworkLookupResponse(
        candidates=[
            ArtworkLookupCandidateRead.model_validate(item, from_attributes=True)
            for item in candidates
        ],
        sources_searched=sources_searched,
        query_used=built.query_used,
        query_source=built.query_source,
        query_strategy=lookup_result.query_strategy,
        artist_fallback=lookup_result.artist_fallback,
        alternate_title=built.alternate_title,
        expected_medium_type=built.expected_medium_type,
        medium_type_filter=built.medium_type_filter,
        notice=notice,
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

    data = normalize_artwork_image_update(data)

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
    artwork.image_master_url = saved.image_master_url
    artwork.image_thumbnail_url = saved.image_thumbnail_url
    artwork.image_width = saved.image_width
    artwork.image_height = saved.image_height
    artwork.image_mime_type = saved.image_mime_type
    artwork.image_file_size = saved.image_file_size
    artwork.captured_at = saved.captured_at
    artwork.captured_date_source = saved.captured_date_source
    artwork.crop_x_percent = None
    artwork.crop_y_percent = None
    artwork.crop_width_percent = None
    artwork.crop_height_percent = None
    db.commit()
    db.refresh(artwork)

    logger.info(
        "artwork image stored artwork_id=%s url=%s bytes=%s",
        artwork_id,
        saved.image_url,
        saved.image_file_size,
    )
    return artwork


@router.patch("/{artwork_id}/image-region", response_model=ArtworkRead)
def set_artwork_image_region(
    artwork_id: int,
    payload: ArtworkImageRegionUpdate,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
) -> Artwork:
    artwork = _get_artwork_or_404(db, artwork_id)
    if not artwork.image_url:
        raise HTTPException(status_code=400, detail="Upload an image before selecting a region.")

    if payload.use_full_image:
        region = None
    else:
        region = ArtworkImageRegion(
            x_percent=payload.x_percent or 0,
            y_percent=payload.y_percent or 0,
            width_percent=payload.width_percent or 0,
            height_percent=payload.height_percent or 0,
        )

    regenerated = regenerate_artwork_derivatives(
        artwork_id=artwork_id,
        image_url=artwork.image_url,
        image_thumbnail_url=artwork.image_thumbnail_url or artwork.image_url,
        image_master_url=artwork.image_master_url,
        region=region,
    )

    artwork.image_width = regenerated.image_width
    artwork.image_height = regenerated.image_height
    artwork.image_file_size = regenerated.image_file_size
    artwork.crop_x_percent = regenerated.crop_x_percent
    artwork.crop_y_percent = regenerated.crop_y_percent
    artwork.crop_width_percent = regenerated.crop_width_percent
    artwork.crop_height_percent = regenerated.crop_height_percent
    db.commit()
    db.refresh(artwork)
    return artwork
