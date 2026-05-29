"""NGA collection visual index build helpers."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image
from sqlalchemy.orm import Session

from app.models import CollectionArtwork, CollectionImageEmbedding
from app.services.visual_embedding import EMBEDDING_MODEL_KEY, VisualEmbeddingError, embed_pil_image
from app.services.visual_index_status import STATE_FILE, THUMBNAIL_CACHE_DIR
from app.sources.museums import NGA_SOURCE_NAME

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
NGA_LOOKUP_INDEX = BACKEND_ROOT / "app" / "data" / "nga_lookup_index.json"
THUMB_TIMEOUT = 20


@dataclass(frozen=True)
class BuildOptions:
    limit: int
    resume: bool
    rebuild: bool
    batch_size: int
    dry_run: bool


@dataclass
class BuildMetrics:
    run_target: int
    processed: int = 0
    new_embeddings: int = 0
    reused_embeddings: int = 0
    skipped: int = 0
    cache_hits: int = 0
    downloads: int = 0
    started_at: float = 0.0

    @property
    def elapsed_seconds(self) -> float:
        if self.started_at <= 0:
            return 0.0
        return max(0.0, time.perf_counter() - self.started_at)


@dataclass(frozen=True)
class IndexState:
    embedding_model: str
    next_offset: int
    updated_at: str


def load_lookup_records() -> list[dict]:
    if not NGA_LOOKUP_INDEX.is_file():
        raise SystemExit(
            f"Missing {NGA_LOOKUP_INDEX}. Run scripts/build_nga_lookup_index.py first."
        )
    records = json.loads(NGA_LOOKUP_INDEX.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise SystemExit("NGA lookup index must be a JSON list.")
    return [record for record in records if isinstance(record, dict)]


def load_state() -> IndexState | None:
    if not STATE_FILE.is_file():
        return None
    try:
        payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    embedding_model = str(payload.get("embedding_model") or "").strip()
    next_offset = payload.get("next_offset")
    updated_at = str(payload.get("updated_at") or "").strip()
    if not embedding_model or not isinstance(next_offset, int) or next_offset < 0:
        return None
    return IndexState(
        embedding_model=embedding_model,
        next_offset=next_offset,
        updated_at=updated_at or datetime.now(UTC).isoformat(),
    )


def save_state(*, embedding_model: str, next_offset: int) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "embedding_model": embedding_model,
        "next_offset": next_offset,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    STATE_FILE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def reset_state() -> None:
    if STATE_FILE.is_file():
        STATE_FILE.unlink()


def _thumbnail_cache_path(object_id: str) -> Path:
    return THUMBNAIL_CACHE_DIR / f"{object_id}.jpg"


def load_thumbnail(object_id: str, url: str | None, *, dry_run: bool) -> tuple[Image.Image | None, bool]:
    cache_path = _thumbnail_cache_path(object_id)
    if cache_path.is_file():
        try:
            return Image.open(cache_path), True
        except Exception:
            cache_path.unlink(missing_ok=True)

    if not url or not url.strip():
        return None, False
    if dry_run:
        logger.info("[dry-run] would download thumbnail object_id=%s url=%s", object_id, url)
        return Image.new("RGB", (8, 8), color=(128, 128, 128)), False

    try:
        response = requests.get(url, timeout=THUMB_TIMEOUT)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content))
        THUMBNAIL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        image.convert("RGB").save(cache_path, format="JPEG", quality=90)
        return image, False
    except Exception as exc:
        logger.warning("thumbnail download failed object_id=%s error=%s", object_id, exc)
        return None, False


def _upsert_artwork(db: Session, record: dict, *, dry_run: bool) -> CollectionArtwork | None:
    object_id = str(record.get("object_id") or "").strip()
    title = (record.get("title") or "").strip()
    if not object_id or not title:
        raise ValueError("Record missing object_id or title")

    if dry_run:
        return CollectionArtwork(
            source_name=NGA_SOURCE_NAME,
            source_object_id=object_id,
            title=title,
            artist=record.get("artist"),
            date=record.get("date"),
            medium=record.get("medium"),
            image_url=record.get("image_url"),
            thumbnail_url=record.get("image_thumbnail_url") or record.get("image_url"),
            object_url=record.get("object_url"),
            rights_label=record.get("rights_label"),
        )

    existing = (
        db.query(CollectionArtwork)
        .filter(
            CollectionArtwork.source_name == NGA_SOURCE_NAME,
            CollectionArtwork.source_object_id == object_id,
        )
        .one_or_none()
    )
    payload = {
        "title": title,
        "artist": record.get("artist"),
        "date": record.get("date"),
        "medium": record.get("medium"),
        "image_url": record.get("image_url"),
        "thumbnail_url": record.get("image_thumbnail_url") or record.get("image_url"),
        "object_url": record.get("object_url"),
        "rights_label": record.get("rights_label"),
        "metadata_json": {
            "accession_number": record.get("accession_number"),
            "begin_year": record.get("begin_year"),
            "end_year": record.get("end_year"),
        },
    }
    if existing:
        for key, value in payload.items():
            setattr(existing, key, value)
        return existing

    artwork = CollectionArtwork(
        source_name=NGA_SOURCE_NAME,
        source_object_id=object_id,
        **payload,
    )
    db.add(artwork)
    db.flush()
    return artwork


def _has_embedding(db: Session, artwork_id: int) -> bool:
    return (
        db.query(CollectionImageEmbedding.id)
        .filter(
            CollectionImageEmbedding.collection_artwork_id == artwork_id,
            CollectionImageEmbedding.embedding_model == EMBEDDING_MODEL_KEY,
        )
        .first()
        is not None
    )


def _delete_embedding(db: Session, artwork_id: int) -> None:
    (
        db.query(CollectionImageEmbedding)
        .filter(
            CollectionImageEmbedding.collection_artwork_id == artwork_id,
            CollectionImageEmbedding.embedding_model == EMBEDDING_MODEL_KEY,
        )
        .delete(synchronize_session=False)
    )


def _ensure_embedding(
    db: Session,
    artwork: CollectionArtwork,
    image: Image.Image,
    image_url: str,
    *,
    rebuild: bool,
    dry_run: bool,
) -> str:
    if dry_run:
        if rebuild:
            return "new"
        return "new"

    if rebuild:
        _delete_embedding(db, artwork.id)

    existing = (
        db.query(CollectionImageEmbedding)
        .filter(
            CollectionImageEmbedding.collection_artwork_id == artwork.id,
            CollectionImageEmbedding.embedding_model == EMBEDDING_MODEL_KEY,
        )
        .one_or_none()
    )
    if existing and not rebuild:
        return "reused"

    vector = embed_pil_image(image)
    if existing:
        existing.embedding_vector = vector
        existing.image_url = image_url
        return "new"

    db.add(
        CollectionImageEmbedding(
            collection_artwork_id=artwork.id,
            embedding_model=EMBEDDING_MODEL_KEY,
            embedding_vector=vector,
            image_url=image_url,
        )
    )
    return "new"


def resolve_start_offset(options: BuildOptions) -> int:
    if not options.resume:
        return 0
    state = load_state()
    if state is None:
        return 0
    if state.embedding_model != EMBEDDING_MODEL_KEY:
        logger.warning(
            "Resume state model %s does not match active model %s; starting from offset 0.",
            state.embedding_model,
            EMBEDDING_MODEL_KEY,
        )
        return 0
    return state.next_offset


def log_progress(metrics: BuildMetrics) -> None:
    logger.info(
        "Indexed %s / %s artworks (new=%s reused=%s skipped=%s)",
        metrics.processed,
        metrics.run_target,
        metrics.new_embeddings,
        metrics.reused_embeddings,
        metrics.skipped,
    )
    print(
        f"Indexed {metrics.processed} / {metrics.run_target} artworks",
        flush=True,
    )


def run_build(db: Session, options: BuildOptions) -> BuildMetrics:
    records = load_lookup_records()
    start_offset = resolve_start_offset(options)
    if options.rebuild and not options.dry_run:
        reset_state()
    elif not options.resume and not options.dry_run:
        reset_state()

    available = max(0, len(records) - start_offset)
    run_target = min(options.limit, available)
    metrics = BuildMetrics(run_target=run_target, started_at=time.perf_counter())

    if run_target == 0:
        logger.info("No NGA records to process (start_offset=%s limit=%s).", start_offset, options.limit)
        print("No NGA records to process.", flush=True)
        return metrics

    selected = records[start_offset : start_offset + run_target]
    logger.info(
        "Starting NGA visual index build model=%s limit=%s resume=%s rebuild=%s dry_run=%s start_offset=%s",
        EMBEDDING_MODEL_KEY,
        options.limit,
        options.resume,
        options.rebuild,
        options.dry_run,
        start_offset,
    )
    print(
        f"Indexing up to {run_target} NGA records with model {EMBEDDING_MODEL_KEY} "
        f"(offset={start_offset}, dry_run={options.dry_run})",
        flush=True,
    )

    for index, record in enumerate(selected, start=1):
        metrics.processed = index
        object_id = str(record.get("object_id") or "").strip()
        try:
            artwork = _upsert_artwork(db, record, dry_run=options.dry_run)
        except ValueError:
            metrics.skipped += 1
            continue
        if artwork is None:
            metrics.skipped += 1
            continue

        if not options.dry_run and not options.rebuild and artwork.id and _has_embedding(db, artwork.id):
            metrics.reused_embeddings += 1
            if index % options.batch_size == 0:
                db.commit()
                log_progress(metrics)
            continue

        image_url = artwork.thumbnail_url or artwork.image_url
        image, cache_hit = load_thumbnail(object_id, image_url, dry_run=options.dry_run)
        if cache_hit:
            metrics.cache_hits += 1
        elif image is not None:
            metrics.downloads += 1
        if image is None:
            metrics.skipped += 1
            if index % options.batch_size == 0:
                if not options.dry_run:
                    db.commit()
                log_progress(metrics)
            continue

        if options.dry_run:
            logger.info("[dry-run] would embed object_id=%s title=%s", object_id, artwork.title)
            metrics.new_embeddings += 1
        else:
            outcome = _ensure_embedding(
                db,
                artwork,
                image,
                image_url or "",
                rebuild=options.rebuild,
                dry_run=options.dry_run,
            )
            if outcome == "new":
                metrics.new_embeddings += 1
            else:
                metrics.reused_embeddings += 1

        if index % options.batch_size == 0:
            if not options.dry_run:
                db.commit()
            log_progress(metrics)

    if not options.dry_run:
        db.commit()
        save_state(embedding_model=EMBEDDING_MODEL_KEY, next_offset=start_offset + run_target)
    log_progress(metrics)
    return metrics
