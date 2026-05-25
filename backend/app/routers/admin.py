from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_listed_admin_user
from app.database import get_db
from app.models import Annotation, Artwork, CulturalEntity, ResearchNote, Visit
from app.schemas.admin import (
    AdminAnnotationListResponse,
    AdminAnnotationRecord,
    AdminArtworkListResponse,
    AdminArtworkRecord,
    AdminBulkDeleteRequest,
    AdminBulkDeleteResponse,
    AdminEntityListResponse,
    AdminEntityRecord,
    AdminListMeta,
    AdminResearchNoteListResponse,
    AdminResearchNoteRecord,
    AdminSummaryRead,
    AdminVisitListResponse,
    AdminVisitRecord,
)
from app.services.admin_bulk_delete import (
    bulk_delete_annotations,
    bulk_delete_artworks,
    bulk_delete_entities,
    bulk_delete_research_notes,
    bulk_delete_visits,
)
from app.services.admin_queries import (
    clamp_limit,
    clamp_offset,
    count_all,
    filter_annotations,
    filter_artworks,
    filter_entities,
    filter_research_notes,
    filter_visits,
    normalize_search,
    paginate,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _list_meta(*, total: int, limit: int, offset: int, search: str | None) -> AdminListMeta:
    return AdminListMeta(total=total, limit=limit, offset=offset, search=search)


@router.get("/summary", response_model=AdminSummaryRead)
def admin_summary(
    _user: Annotated[dict[str, str | None], Depends(require_listed_admin_user)],
    db: Session = Depends(get_db),
) -> AdminSummaryRead:
    counts = count_all(db)
    return AdminSummaryRead(**counts)


@router.get("/visits", response_model=AdminVisitListResponse)
def admin_list_visits(
    _user: Annotated[dict[str, str | None], Depends(require_listed_admin_user)],
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
) -> AdminVisitListResponse:
    cleaned_search = normalize_search(search)
    safe_limit = clamp_limit(limit)
    safe_offset = clamp_offset(offset)
    query = filter_visits(db.query(Visit).order_by(Visit.created_at.desc()), cleaned_search)
    records, total = paginate(query, limit=safe_limit, offset=safe_offset)
    return AdminVisitListResponse(
        records=[AdminVisitRecord.model_validate(item) for item in records],
        meta=_list_meta(total=total, limit=safe_limit, offset=safe_offset, search=cleaned_search),
    )


@router.get("/artworks", response_model=AdminArtworkListResponse)
def admin_list_artworks(
    _user: Annotated[dict[str, str | None], Depends(require_listed_admin_user)],
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
) -> AdminArtworkListResponse:
    cleaned_search = normalize_search(search)
    safe_limit = clamp_limit(limit)
    safe_offset = clamp_offset(offset)
    query = filter_artworks(db.query(Artwork).order_by(Artwork.created_at.desc()), cleaned_search)
    records, total = paginate(query, limit=safe_limit, offset=safe_offset)
    return AdminArtworkListResponse(
        records=[AdminArtworkRecord.model_validate(item) for item in records],
        meta=_list_meta(total=total, limit=safe_limit, offset=safe_offset, search=cleaned_search),
    )


@router.get("/annotations", response_model=AdminAnnotationListResponse)
def admin_list_annotations(
    _user: Annotated[dict[str, str | None], Depends(require_listed_admin_user)],
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
) -> AdminAnnotationListResponse:
    cleaned_search = normalize_search(search)
    safe_limit = clamp_limit(limit)
    safe_offset = clamp_offset(offset)
    query = filter_annotations(
        db.query(Annotation).order_by(Annotation.created_at.desc()),
        cleaned_search,
    )
    records, total = paginate(query, limit=safe_limit, offset=safe_offset)
    return AdminAnnotationListResponse(
        records=[AdminAnnotationRecord.model_validate(item) for item in records],
        meta=_list_meta(total=total, limit=safe_limit, offset=safe_offset, search=cleaned_search),
    )


@router.get("/entities", response_model=AdminEntityListResponse)
def admin_list_entities(
    _user: Annotated[dict[str, str | None], Depends(require_listed_admin_user)],
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
) -> AdminEntityListResponse:
    cleaned_search = normalize_search(search)
    safe_limit = clamp_limit(limit)
    safe_offset = clamp_offset(offset)
    query = filter_entities(
        db.query(CulturalEntity).order_by(CulturalEntity.created_at.desc()),
        cleaned_search,
    )
    records, total = paginate(query, limit=safe_limit, offset=safe_offset)
    return AdminEntityListResponse(
        records=[AdminEntityRecord.model_validate(item) for item in records],
        meta=_list_meta(total=total, limit=safe_limit, offset=safe_offset, search=cleaned_search),
    )


@router.get("/research-notes", response_model=AdminResearchNoteListResponse)
def admin_list_research_notes(
    _user: Annotated[dict[str, str | None], Depends(require_listed_admin_user)],
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
) -> AdminResearchNoteListResponse:
    cleaned_search = normalize_search(search)
    safe_limit = clamp_limit(limit)
    safe_offset = clamp_offset(offset)
    query = filter_research_notes(
        db.query(ResearchNote).order_by(ResearchNote.created_at.desc()),
        cleaned_search,
    )
    records, total = paginate(query, limit=safe_limit, offset=safe_offset)
    return AdminResearchNoteListResponse(
        records=[AdminResearchNoteRecord.model_validate(item) for item in records],
        meta=_list_meta(total=total, limit=safe_limit, offset=safe_offset, search=cleaned_search),
    )


@router.post("/visits/bulk-delete", response_model=AdminBulkDeleteResponse)
def admin_bulk_delete_visits(
    payload: AdminBulkDeleteRequest,
    _user: Annotated[dict[str, str | None], Depends(require_listed_admin_user)],
    db: Session = Depends(get_db),
) -> AdminBulkDeleteResponse:
    deleted_count = bulk_delete_visits(db, payload.ids)
    return AdminBulkDeleteResponse(deleted_count=deleted_count)


@router.post("/artworks/bulk-delete", response_model=AdminBulkDeleteResponse)
def admin_bulk_delete_artworks(
    payload: AdminBulkDeleteRequest,
    _user: Annotated[dict[str, str | None], Depends(require_listed_admin_user)],
    db: Session = Depends(get_db),
) -> AdminBulkDeleteResponse:
    deleted_count = bulk_delete_artworks(db, payload.ids)
    return AdminBulkDeleteResponse(deleted_count=deleted_count)


@router.post("/annotations/bulk-delete", response_model=AdminBulkDeleteResponse)
def admin_bulk_delete_annotations(
    payload: AdminBulkDeleteRequest,
    _user: Annotated[dict[str, str | None], Depends(require_listed_admin_user)],
    db: Session = Depends(get_db),
) -> AdminBulkDeleteResponse:
    deleted_count = bulk_delete_annotations(db, payload.ids)
    return AdminBulkDeleteResponse(deleted_count=deleted_count)


@router.post("/entities/bulk-delete", response_model=AdminBulkDeleteResponse)
def admin_bulk_delete_entities(
    payload: AdminBulkDeleteRequest,
    _user: Annotated[dict[str, str | None], Depends(require_listed_admin_user)],
    db: Session = Depends(get_db),
) -> AdminBulkDeleteResponse:
    deleted_count = bulk_delete_entities(db, payload.ids)
    return AdminBulkDeleteResponse(deleted_count=deleted_count)


@router.post("/research-notes/bulk-delete", response_model=AdminBulkDeleteResponse)
def admin_bulk_delete_research_notes(
    payload: AdminBulkDeleteRequest,
    _user: Annotated[dict[str, str | None], Depends(require_listed_admin_user)],
    db: Session = Depends(get_db),
) -> AdminBulkDeleteResponse:
    deleted_count = bulk_delete_research_notes(db, payload.ids)
    return AdminBulkDeleteResponse(deleted_count=deleted_count)
