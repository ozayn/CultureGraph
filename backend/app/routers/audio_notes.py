"""Audio note upload, transcription, and interpretation."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin_user
from app.database import get_db
from app.models import Artwork, AudioNote, Visit
from app.schemas import (
    AudioInterpretationRead,
    AudioNoteRead,
    AudioNoteTranscriptUpdate,
    AudioTranscribeRequest,
)
from app.services.audio_interpretation import (
    AudioInterpretationError,
    build_interpretation_context,
    get_interpretation_provider,
)
from app.services.audio_transcription import (
    TranscriptionError,
    get_transcription_provider,
    resolve_audio_file_path,
)
from app.services.audio_upload import (
    read_audio_upload,
    remove_audio_note_file,
    save_audio_note_file,
    validate_audio_duration,
    validate_audio_upload,
)

router = APIRouter(prefix="/audio-notes", tags=["audio-notes"])


def _get_audio_note_or_404(db: Session, note_id: int) -> AudioNote:
    note = db.get(AudioNote, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Audio note not found")
    return note


def _validate_parent_ids(
    db: Session,
    *,
    visit_id: int | None,
    artwork_id: int | None,
) -> tuple[int | None, int | None]:
    if visit_id is None and artwork_id is None:
        raise HTTPException(status_code=400, detail="Provide visit_id or artwork_id.")
    if visit_id is not None and not db.get(Visit, visit_id):
        raise HTTPException(status_code=404, detail="Visit not found")
    if artwork_id is not None and not db.get(Artwork, artwork_id):
        raise HTTPException(status_code=404, detail="Artwork not found")
    return visit_id, artwork_id


def _audio_note_read(note: AudioNote) -> AudioNoteRead:
    interpretation = None
    if isinstance(note.interpretation_json, dict):
        try:
            interpretation = AudioInterpretationRead.model_validate(note.interpretation_json)
        except Exception:
            interpretation = None
    return AudioNoteRead(
        id=note.id,
        visit_id=note.visit_id,
        artwork_id=note.artwork_id,
        audio_url=note.audio_url,
        duration_seconds=note.duration_seconds,
        transcript=note.transcript,
        cleaned_note=note.cleaned_note,
        interpretation=interpretation,
        created_at=note.created_at,
    )


def _interpretation_context(db: Session, note: AudioNote) -> dict:
    artwork = db.get(Artwork, note.artwork_id) if note.artwork_id else None
    visit = db.get(Visit, note.visit_id) if note.visit_id else None
    if artwork and artwork.visit_id and not visit:
        visit = db.get(Visit, artwork.visit_id)
    return build_interpretation_context(
        artwork_title=artwork.title if artwork else None,
        artwork_artist=artwork.artist if artwork else None,
        museum_name=visit.museum_name if visit else None,
        museum_gallery=artwork.museum_gallery if artwork else None,
        visit_notes=visit.notes if visit else None,
    )


@router.get("", response_model=list[AudioNoteRead])
def list_audio_notes(
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
    visit_id: int | None = Query(default=None),
    artwork_id: int | None = Query(default=None),
) -> list[AudioNoteRead]:
    if visit_id is None and artwork_id is None:
        raise HTTPException(status_code=400, detail="Provide visit_id or artwork_id.")
    query = db.query(AudioNote).order_by(AudioNote.created_at.desc())
    if visit_id is not None:
        query = query.filter(AudioNote.visit_id == visit_id)
    if artwork_id is not None:
        query = query.filter(AudioNote.artwork_id == artwork_id)
    return [_audio_note_read(note) for note in query.all()]


@router.post("", response_model=AudioNoteRead, status_code=status.HTTP_201_CREATED)
async def create_audio_note(
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    visit_id: Annotated[int | None, Form()] = None,
    artwork_id: Annotated[int | None, Form()] = None,
    duration_seconds: Annotated[float | None, Form()] = None,
) -> AudioNoteRead:
    visit_id, artwork_id = _validate_parent_ids(db, visit_id=visit_id, artwork_id=artwork_id)
    duration = validate_audio_duration(duration_seconds)
    suffix = validate_audio_upload(file.filename, file.content_type)
    data = await read_audio_upload(file)
    audio_url, _path = save_audio_note_file(data, suffix=suffix)

    note = AudioNote(
        visit_id=visit_id,
        artwork_id=artwork_id,
        audio_url=audio_url,
        duration_seconds=duration,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return _audio_note_read(note)


@router.patch("/{note_id}", response_model=AudioNoteRead)
def update_audio_note_transcript(
    note_id: int,
    payload: AudioNoteTranscriptUpdate,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
) -> AudioNoteRead:
    note = _get_audio_note_or_404(db, note_id)
    if payload.transcript is not None:
        note.transcript = payload.transcript.strip() or None
    if payload.cleaned_note is not None:
        note.cleaned_note = payload.cleaned_note.strip() or None
    db.commit()
    db.refresh(note)
    return _audio_note_read(note)


@router.post("/{note_id}/transcribe", response_model=AudioNoteRead)
async def transcribe_audio_note(
    note_id: int,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
    payload: AudioTranscribeRequest | None = None,
) -> AudioNoteRead:
    note = _get_audio_note_or_404(db, note_id)
    manual = (payload.transcript if payload else None) or ""
    manual = manual.strip()
    if manual:
        note.transcript = manual
        db.commit()
        db.refresh(note)
        return _audio_note_read(note)

    provider = get_transcription_provider()
    try:
        path = resolve_audio_file_path(note.audio_url)
        transcript = await provider.transcribe_file(path, filename=path.name)
    except TranscriptionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    note.transcript = transcript
    db.commit()
    db.refresh(note)
    return _audio_note_read(note)


@router.post("/{note_id}/interpret", response_model=AudioNoteRead)
async def interpret_audio_note(
    note_id: int,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
) -> AudioNoteRead:
    note = _get_audio_note_or_404(db, note_id)
    transcript = (note.transcript or "").strip()
    if not transcript:
        raise HTTPException(status_code=400, detail="Transcribe the note before interpreting.")

    provider = get_interpretation_provider()
    try:
        draft = await provider.interpret(
            transcript=transcript,
            context=_interpretation_context(db, note),
        )
    except AudioInterpretationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    note.cleaned_note = draft.cleaned_note
    note.interpretation_json = draft.model_dump(mode="json")
    db.commit()
    db.refresh(note)
    return _audio_note_read(note)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_audio_note(
    note_id: int,
    _user: Annotated[dict[str, str], Depends(require_admin_user)],
    db: Session = Depends(get_db),
) -> None:
    note = _get_audio_note_or_404(db, note_id)
    remove_audio_note_file(note.audio_url)
    db.delete(note)
    db.commit()
