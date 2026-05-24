from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import require_admin_user

from app.schemas import MuseumNotesImportRequest, MuseumNotesImportResponse
from app.services.museum_notes_import import get_museum_notes_import_provider
from app.services.research import ResearchConfigurationError, ResearchProviderError

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/museum-notes", response_model=MuseumNotesImportResponse)
async def extract_museum_notes(
    payload: MuseumNotesImportRequest,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
) -> MuseumNotesImportResponse:
    provider = get_museum_notes_import_provider()

    try:
        return await provider.extract(payload)
    except ResearchConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ResearchProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
