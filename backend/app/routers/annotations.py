from typing import Annotated

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin_user

from app.database import get_db
from app.models import Annotation, Artwork
from app.schemas import AnnotationCreate, AnnotationRead, AnnotationUpdate
from app.services.annotation_links import apply_annotation_payload

logger = logging.getLogger(__name__)

router = APIRouter(tags=["annotations"])


def _get_artwork_or_404(db: Session, artwork_id: int) -> Artwork:
    artwork = db.get(Artwork, artwork_id)
    if not artwork:
        raise HTTPException(status_code=404, detail="Artwork not found")
    return artwork


@router.get("/artworks/{artwork_id}/annotations", response_model=list[AnnotationRead])
def list_annotations(artwork_id: int, db: Session = Depends(get_db)) -> list[Annotation]:
    _get_artwork_or_404(db, artwork_id)
    return (
        db.query(Annotation)
        .filter(Annotation.artwork_id == artwork_id)
        .order_by(Annotation.created_at.asc())
        .all()
    )


@router.post(
    "/artworks/{artwork_id}/annotations",
    response_model=AnnotationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_annotation(
    artwork_id: int,
    payload: AnnotationCreate,
    user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
) -> Annotation:
    logger.info(
        "annotation create requested artwork_id=%s user=%s category=%s",
        artwork_id,
        user.get("email"),
        payload.category.value,
    )
    artwork = _get_artwork_or_404(db, artwork_id)
    data = apply_annotation_payload(db, artwork, payload.model_dump())
    annotation = Annotation(artwork_id=artwork_id, **data)
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    logger.info(
        "annotation created id=%s artwork_id=%s x=%.2f y=%.2f",
        annotation.id,
        artwork_id,
        annotation.x_percent,
        annotation.y_percent,
    )
    return annotation


def _get_annotation_or_404(db: Session, annotation_id: int, artwork_id: int | None = None) -> Annotation:
    annotation = db.get(Annotation, annotation_id)
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")
    if artwork_id is not None and annotation.artwork_id != artwork_id:
        raise HTTPException(status_code=404, detail="Annotation not found for this artwork")
    return annotation


def _apply_annotation_update(
    db: Session,
    artwork: Artwork,
    annotation: Annotation,
    payload: AnnotationUpdate,
) -> None:
    data = apply_annotation_payload(
        db,
        artwork,
        payload.model_dump(exclude_unset=True),
    )
    for key, value in data.items():
        setattr(annotation, key, value)


@router.put("/annotations/{annotation_id}", response_model=AnnotationRead)
@router.patch("/annotations/{annotation_id}", response_model=AnnotationRead)
def update_annotation(
    annotation_id: int,
    payload: AnnotationUpdate,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
) -> Annotation:
    annotation = _get_annotation_or_404(db, annotation_id)
    artwork = _get_artwork_or_404(db, annotation.artwork_id)
    _apply_annotation_update(db, artwork, annotation, payload)
    db.commit()
    db.refresh(annotation)
    return annotation


@router.put(
    "/artworks/{artwork_id}/annotations/{annotation_id}",
    response_model=AnnotationRead,
)
@router.patch(
    "/artworks/{artwork_id}/annotations/{annotation_id}",
    response_model=AnnotationRead,
)
def update_artwork_annotation(
    artwork_id: int,
    annotation_id: int,
    payload: AnnotationUpdate,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
) -> Annotation:
    _get_artwork_or_404(db, artwork_id)
    annotation = _get_annotation_or_404(db, annotation_id, artwork_id)
    artwork = _get_artwork_or_404(db, artwork_id)
    _apply_annotation_update(db, artwork, annotation, payload)
    db.commit()
    db.refresh(annotation)
    return annotation


@router.delete("/annotations/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_annotation(
    annotation_id: int,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
) -> None:
    annotation = _get_annotation_or_404(db, annotation_id)
    db.delete(annotation)
    db.commit()


@router.delete(
    "/artworks/{artwork_id}/annotations/{annotation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_artwork_annotation(
    artwork_id: int,
    annotation_id: int,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
) -> None:
    _get_artwork_or_404(db, artwork_id)
    annotation = _get_annotation_or_404(db, annotation_id, artwork_id)
    db.delete(annotation)
    db.commit()
