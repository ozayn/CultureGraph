from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Artwork, CulturalEntity


def validate_annotation_links(
    db: Session,
    artwork: Artwork,
    *,
    linked_entity_ids: list[int] | None,
) -> None:
    if not linked_entity_ids:
        return

    if artwork.visit_id is None:
        raise HTTPException(
            status_code=400,
            detail="Link cultural entities after this artwork is attached to a visit.",
        )

    entities = (
        db.query(CulturalEntity.id)
        .filter(
            CulturalEntity.id.in_(linked_entity_ids),
            CulturalEntity.visit_id == artwork.visit_id,
        )
        .all()
    )
    found_ids = {row[0] for row in entities}
    missing = [entity_id for entity_id in linked_entity_ids if entity_id not in found_ids]
    if missing:
        raise HTTPException(
            status_code=400,
            detail="One or more linked entities were not found on this visit.",
        )


def apply_annotation_payload(db: Session, artwork: Artwork, data: dict) -> dict:
    if "linked_entity_ids" in data:
        validate_annotation_links(
            db,
            artwork,
            linked_entity_ids=data["linked_entity_ids"],
        )
    return data
