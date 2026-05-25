import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import require_admin_user

from app.schemas import MuseumNotesImportRequest, MuseumNotesImportResponse
from app.services.museum_notes_import import get_museum_notes_import_provider
from app.services.research import ResearchConfigurationError, ResearchProviderError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/museum-notes", response_model=MuseumNotesImportResponse)
async def extract_museum_notes(
    payload: MuseumNotesImportRequest,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
) -> MuseumNotesImportResponse:
    started = time.perf_counter()
    provider = get_museum_notes_import_provider()
    provider_name = type(provider).__name__

    logger.info(
        "museum-notes import started provider=%s text_chars=%d museum=%s",
        provider_name,
        len(payload.text),
        payload.default_museum,
    )

    try:
        result = await provider.extract(payload)
    except ResearchConfigurationError as exc:
        logger.exception("museum-notes import configuration error")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ResearchProviderError as exc:
        logger.warning("museum-notes import provider error: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    else:
        elapsed = time.perf_counter() - started
        logger.info(
            "museum-notes import finished source=%s entities=%d elapsed=%.2fs ai_warning=%s",
            result.source,
            len(result.entities),
            elapsed,
            bool(result.ai_warning),
        )
        return result
