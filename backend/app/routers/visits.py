from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin_user
from app.database import get_db
from app.models import Visit
from app.schemas import VisitCreate, VisitRead, VisitUpdate

router = APIRouter(prefix="/visits", tags=["visits"])


@router.get("", response_model=list[VisitRead])
def list_visits(db: Session = Depends(get_db)) -> list[Visit]:
    return db.query(Visit).order_by(Visit.visit_date.desc()).all()


@router.post("", response_model=VisitRead, status_code=status.HTTP_201_CREATED)
def create_visit(
    payload: VisitCreate,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
) -> Visit:
    visit = Visit(**payload.model_dump())
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return visit


@router.get("/{visit_id}", response_model=VisitRead)
def get_visit(visit_id: int, db: Session = Depends(get_db)) -> Visit:
    visit = db.get(Visit, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    return visit


@router.put("/{visit_id}", response_model=VisitRead)
def update_visit(
    visit_id: int,
    payload: VisitUpdate,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
) -> Visit:
    visit = db.get(Visit, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(visit, key, value)

    db.commit()
    db.refresh(visit)
    return visit


@router.delete("/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_visit(
    visit_id: int,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
) -> None:
    visit = db.get(Visit, visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    db.delete(visit)
    db.commit()
