from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin_user
from app.database import get_db
from app.models import CulturalEntity, Visit
from app.schemas import CulturalEntityCreate, CulturalEntityRead

router = APIRouter(prefix="/cultural-entities", tags=["cultural-entities"])


@router.get("", response_model=list[CulturalEntityRead])
def list_cultural_entities(
    visit_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[CulturalEntity]:
    query = db.query(CulturalEntity)
    if visit_id is not None:
        query = query.filter(CulturalEntity.visit_id == visit_id)
    return query.order_by(CulturalEntity.created_at.asc()).all()


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
