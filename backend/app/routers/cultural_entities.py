from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin_user
from app.database import get_db
from app.models import CulturalEntity, Visit
from app.schemas import (
    CulturalEntityCreate,
    CulturalEntityRead,
    CulturalEntityUpdate,
)

router = APIRouter(prefix="/cultural-entities", tags=["cultural-entities"])


def _get_entity_or_404(db: Session, entity_id: int) -> CulturalEntity:
    entity = db.get(CulturalEntity, entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Cultural entity not found")
    return entity


@router.get("", response_model=list[CulturalEntityRead])
def list_cultural_entities(
    visit_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[CulturalEntity]:
    query = db.query(CulturalEntity)
    if visit_id is not None:
        query = query.filter(CulturalEntity.visit_id == visit_id)
    return query.order_by(CulturalEntity.created_at.asc()).all()


@router.get("/{entity_id}", response_model=CulturalEntityRead)
def get_cultural_entity(entity_id: int, db: Session = Depends(get_db)) -> CulturalEntity:
    return _get_entity_or_404(db, entity_id)


@router.post("", response_model=CulturalEntityRead, status_code=status.HTTP_201_CREATED)
def create_cultural_entity(
    payload: CulturalEntityCreate,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
) -> CulturalEntity:
    if payload.entity_type.value == "artwork":
        raise HTTPException(
            status_code=400,
            detail="Artwork entries should be saved via /api/artworks.",
        )

    if not db.get(Visit, payload.visit_id):
        raise HTTPException(status_code=400, detail="Visit not found")

    entity = CulturalEntity(**payload.model_dump())
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


@router.put("/{entity_id}", response_model=CulturalEntityRead)
@router.patch("/{entity_id}", response_model=CulturalEntityRead)
def update_cultural_entity(
    entity_id: int,
    payload: CulturalEntityUpdate,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
) -> CulturalEntity:
    entity = _get_entity_or_404(db, entity_id)
    data = payload.model_dump(exclude_unset=True)

    if "entity_type" in data and data["entity_type"] is not None:
        if data["entity_type"].value == "artwork":
            raise HTTPException(
                status_code=400,
                detail="Artwork entries should be saved via /api/artworks.",
            )

    for key, value in data.items():
        setattr(entity, key, value)

    db.commit()
    db.refresh(entity)
    return entity


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cultural_entity(
    entity_id: int,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
) -> None:
    entity = _get_entity_or_404(db, entity_id)
    db.delete(entity)
    db.commit()
