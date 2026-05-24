from fastapi import APIRouter, Query

from app.data.dc_museums import search_dc_museums
from app.schemas import MuseumRead

router = APIRouter(prefix="/museums", tags=["museums"])


@router.get("", response_model=list[MuseumRead])
def list_museums(query: str = Query(default="", max_length=100)) -> list[MuseumRead]:
    return search_dc_museums(query, limit=10)
