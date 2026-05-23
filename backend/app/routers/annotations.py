from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Annotation, Artwork
from app.schemas import AnnotationCreate, AnnotationRead, AnnotationUpdate

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
    artwork_id: int, payload: AnnotationCreate, db: Session = Depends(get_db)
) -> Annotation:
    _get_artwork_or_404(db, artwork_id)
    annotation = Annotation(artwork_id=artwork_id, **payload.model_dump())
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return annotation


@router.put("/annotations/{annotation_id}", response_model=AnnotationRead)
def update_annotation(
    annotation_id: int, payload: AnnotationUpdate, db: Session = Depends(get_db)
) -> Annotation:
    annotation = db.get(Annotation, annotation_id)
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(annotation, key, value)

    db.commit()
    db.refresh(annotation)
    return annotation


@router.delete("/annotations/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_annotation(annotation_id: int, db: Session = Depends(get_db)) -> None:
    annotation = db.get(Annotation, annotation_id)
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")
    db.delete(annotation)
    db.commit()
