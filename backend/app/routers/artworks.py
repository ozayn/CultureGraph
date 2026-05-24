import os
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin_user

from app.config import settings
from app.database import get_db
from app.models import Artwork, Visit
from app.schemas import ArtworkCreate, ArtworkRead, ArtworkUpdate

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


@router.put("/{artwork_id}", response_model=ArtworkRead)
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
    db.delete(artwork)
    db.commit()


@router.post("/{artwork_id}/image", response_model=ArtworkRead)
async def upload_artwork_image(
    artwork_id: int,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Artwork:
    artwork = _get_artwork_or_404(db, artwork_id)

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "image.jpg").suffix or ".jpg"
    filename = f"{uuid.uuid4().hex}{suffix}"
    filepath = upload_dir / filename

    content = await file.read()
    filepath.write_bytes(content)

    artwork.image_url = f"/uploads/{filename}"
    db.commit()
    db.refresh(artwork)
    return artwork
