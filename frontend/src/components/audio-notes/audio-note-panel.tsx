"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { Mic, Pause, Play, Square, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import {
  AUDIO_NOTE_MAX_DURATION_SECONDS,
  blobToUploadFile,
  formatRecordingTimer,
  GalleryAudioRecorder,
} from "@/lib/audio-recorder";
import { resolveImageUrl } from "@/lib/media-url";
import { suggestedAnnotationToAnnotationPayload } from "@/lib/research-suggestions";
import type {
  AiSuggestedAnnotation,
  Annotation,
  Artwork,
  AudioInterpretation,
  AudioNote,
  CulturalEntity,
  Visit,
} from "@/lib/types";

type PanelStep = "record" | "review" | "interpretation";

interface AudioNotePanelProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  artworkId?: number | null;
  visitId?: number | null;
  culturalEntities?: CulturalEntity[];
  existingPersonalNote?: string | null;
  existingVisitNotes?: string | null;
  onPersonalNoteSaved?: (text: string) => void;
  onVisitNotesSaved?: (text: string) => void;
  onAnnotationsCreated?: (annotations: Annotation[]) => void;
}

function normalizeSuggestions(raw: AiSuggestedAnnotation[]): AiSuggestedAnnotation[] {
  return raw.map((item) => ({
    ...item,
    confidence: item.confidence ?? 0.5,
    suggested_position: item.suggested_position ?? {
      x_percent: null,
      y_percent: null,
      reason: null,
    },
    tags: item.tags ?? [],
    linked_concept_names: item.linked_concept_names ?? [],
    status: item.status ?? "pending",
  }));
}

export function AudioNotePanel({
  open,
  onOpenChange,
  artworkId = null,
  visitId = null,
  culturalEntities = [],
  existingPersonalNote = null,
  existingVisitNotes = null,
  onPersonalNoteSaved,
  onVisitNotesSaved,
  onAnnotationsCreated,
}: AudioNotePanelProps) {
  const recorderRef = useRef(new GalleryAudioRecorder());
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const [step, setStep] = useState<PanelStep>("record");
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [localBlob, setLocalBlob] = useState<Blob | null>(null);
  const [localMimeType, setLocalMimeType] = useState("audio/webm");
  const [localDuration, setLocalDuration] = useState<number | null>(null);
  const [localPreviewUrl, setLocalPreviewUrl] = useState<string | null>(null);
  const [savedNote, setSavedNote] = useState<AudioNote | null>(null);
  const [transcript, setTranscript] = useState("");
  const [interpretation, setInterpretation] = useState<AudioInterpretation | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);

  const playbackUrl = useMemo(() => {
    if (localPreviewUrl) return localPreviewUrl;
    if (savedNote?.audio_url) return resolveImageUrl(savedNote.audio_url);
    return null;
  }, [localPreviewUrl, savedNote?.audio_url]);

  const entityLinks = useMemo(() => {
    const names = interpretation?.related_entities ?? [];
    if (names.length === 0) return [];
    return names.map((name) => {
      const match = culturalEntities.find(
        (entity) => entity.name.trim().toLowerCase() === name.trim().toLowerCase()
      );
      return { name, entity: match ?? null };
    });
  }, [culturalEntities, interpretation?.related_entities]);

  useEffect(() => {
    if (!open) {
      resetPanel();
    }
  }, [open]);

  useEffect(() => {
    return () => {
      if (localPreviewUrl) URL.revokeObjectURL(localPreviewUrl);
    };
  }, [localPreviewUrl]);

  function resetPanel() {
    recorderRef.current.discard();
    if (localPreviewUrl) URL.revokeObjectURL(localPreviewUrl);
    setStep("record");
    setRecording(false);
    setElapsed(0);
    setLocalBlob(null);
    setLocalMimeType("audio/webm");
    setLocalDuration(null);
    setLocalPreviewUrl(null);
    setSavedNote(null);
    setTranscript("");
    setInterpretation(null);
    setBusy(null);
    setError(null);
    setSuccess(null);
    setPlaying(false);
  }

  async function startRecording() {
    setError(null);
    setSuccess(null);
    try {
      await recorderRef.current.start(
        (seconds) => setElapsed(seconds),
        () => {
          void stopRecording();
        }
      );
      setRecording(true);
      setElapsed(0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start recording.");
    }
  }

  async function stopRecording() {
    if (!recording) return;
    setBusy("stop");
    setError(null);
    try {
      const result = await recorderRef.current.stop();
      if (localPreviewUrl) URL.revokeObjectURL(localPreviewUrl);
      const preview = URL.createObjectURL(result.blob);
      setLocalBlob(result.blob);
      setLocalMimeType(result.mimeType);
      setLocalDuration(result.durationSeconds);
      setLocalPreviewUrl(preview);
      setRecording(false);
      setElapsed(result.durationSeconds);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not stop recording.");
      setRecording(false);
    } finally {
      setBusy(null);
    }
  }

  function discardRecording() {
    recorderRef.current.discard();
    if (localPreviewUrl) URL.revokeObjectURL(localPreviewUrl);
    setLocalBlob(null);
    setLocalPreviewUrl(null);
    setLocalDuration(null);
    setElapsed(0);
    setRecording(false);
    setSavedNote(null);
    setTranscript("");
    setInterpretation(null);
    setStep("record");
    setPlaying(false);
  }

  async function togglePlayback() {
    if (!playbackUrl || !audioRef.current) return;
    if (playing) {
      audioRef.current.pause();
      setPlaying(false);
      return;
    }
    try {
      await audioRef.current.play();
      setPlaying(true);
    } catch {
      setError("Could not play recording.");
    }
  }

  async function uploadRecording() {
    if (!localBlob) return;
    setBusy("upload");
    setError(null);
    try {
      const file = blobToUploadFile(localBlob, localMimeType);
      const note = await api.upload<AudioNote>("/api/audio-notes", file, {
        artwork_id: artworkId ? String(artworkId) : undefined,
        visit_id: visitId ? String(visitId) : undefined,
        duration_seconds: localDuration ? String(Math.round(localDuration * 100) / 100) : undefined,
      });
      setSavedNote(note);
      setTranscript(note.transcript ?? "");
      setInterpretation(note.interpretation ?? null);
      setStep("review");
      setSuccess("Recording saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not upload recording.");
    } finally {
      setBusy(null);
    }
  }

  async function transcribeAndInterpret() {
    if (!savedNote) return;
    setBusy("transcribe");
    setError(null);
    setSuccess(null);
    try {
      let note = savedNote;
      if (transcript.trim()) {
        note = await api.post<AudioNote>(`/api/audio-notes/${note.id}/transcribe`, {
          transcript: transcript.trim(),
        });
      } else {
        try {
          note = await api.post<AudioNote>(`/api/audio-notes/${note.id}/transcribe`);
        } catch (e) {
          const message = e instanceof Error ? e.message : "";
          if (!message.toLowerCase().includes("openai") && !message.toLowerCase().includes("manual")) {
            throw e;
          }
          setError(
            message ||
              "Transcription is unavailable. Type what you said below, then try again."
          );
          setBusy(null);
          return;
        }
      }
      setSavedNote(note);
      setTranscript(note.transcript ?? transcript);
      setBusy("interpret");
      note = await api.post<AudioNote>(`/api/audio-notes/${note.id}/interpret`);
      setSavedNote(note);
      setTranscript(note.transcript ?? "");
      setInterpretation(note.interpretation ?? null);
      setStep("interpretation");
      setSuccess("Transcript ready for review.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not transcribe or interpret.");
    } finally {
      setBusy(null);
    }
  }

  async function savePersonalNote() {
    const text = (interpretation?.cleaned_note || transcript).trim();
    if (!text) {
      setError("Add a transcript or interpretation before saving.");
      return;
    }

    setBusy("save-note");
    setError(null);
    try {
      if (artworkId) {
        const prefix = existingPersonalNote?.trim() ? `${existingPersonalNote.trim()}\n\n` : "";
        const updated = await api.put<Artwork>(`/api/artworks/${artworkId}`, {
          personal_notes: `${prefix}${text}`,
        });
        onPersonalNoteSaved?.(updated.personal_notes ?? text);
      } else if (visitId) {
        const prefix = existingVisitNotes?.trim() ? `${existingVisitNotes.trim()}\n\n` : "";
        const updated = await api.put<Visit>(`/api/visits/${visitId}`, {
          notes: `${prefix}${text}`,
        });
        onVisitNotesSaved?.(updated.notes ?? text);
      }
      if (savedNote && transcript.trim()) {
        await api.patch(`/api/audio-notes/${savedNote.id}`, {
          transcript: transcript.trim(),
          cleaned_note: interpretation?.cleaned_note ?? null,
        });
      }
      setSuccess("Saved as personal note.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save note.");
    } finally {
      setBusy(null);
    }
  }

  async function createSuggestedAnnotations() {
    if (!artworkId || !interpretation?.suggested_annotations?.length) return;
    setBusy("annotations");
    setError(null);
    try {
      const created: Annotation[] = [];
      for (const suggestion of normalizeSuggestions(interpretation.suggested_annotations)) {
        const payload = suggestedAnnotationToAnnotationPayload(suggestion);
        const annotation = await api.post<Annotation>(
          `/api/artworks/${artworkId}/annotations`,
          payload
        );
        created.push(annotation);
      }
      onAnnotationsCreated?.(created);
      setSuccess(`Created ${created.length} annotation${created.length === 1 ? "" : "s"}.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create annotations.");
    } finally {
      setBusy(null);
    }
  }

  async function deleteSavedNote() {
    if (savedNote) {
      setBusy("delete");
      try {
        await api.delete(`/api/audio-notes/${savedNote.id}`);
      } catch {
        // Local discard still clears UI even if server delete fails.
      } finally {
        setBusy(null);
      }
    }
    discardRecording();
  }

  const title = artworkId ? "Record artwork note" : "Record visit note";
  const description = artworkId
    ? "Speak observations while you are in front of the work."
    : "Capture quick thoughts about this museum visit.";

  return (
    <BottomSheet open={open} onOpenChange={onOpenChange} title={title} description={description}>
      <div className="space-y-4 pb-2">
        {step === "record" ? (
          <>
            <div className="rounded-xl border border-border bg-muted/30 px-4 py-6 text-center">
              <p className="text-4xl font-medium tabular-nums">
                {formatRecordingTimer(recording ? elapsed : localDuration ?? 0)}
              </p>
              <p className="mt-2 text-sm text-muted-foreground">
                {recording
                  ? "Recording…"
                  : localBlob
                    ? "Review your recording"
                    : `Up to ${Math.floor(AUDIO_NOTE_MAX_DURATION_SECONDS / 60)} minutes`}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2">
              {!recording && !localBlob ? (
                <Button
                  type="button"
                  size="touch"
                  className="col-span-2"
                  onClick={() => void startRecording()}
                >
                  <Mic className="size-5" />
                  Start recording
                </Button>
              ) : null}

              {recording ? (
                <Button
                  type="button"
                  size="touch"
                  variant="destructive"
                  className="col-span-2"
                  disabled={busy === "stop"}
                  onClick={() => void stopRecording()}
                >
                  <Square className="size-5" />
                  Stop
                </Button>
              ) : null}

              {localBlob && !recording ? (
                <>
                  <Button
                    type="button"
                    size="touch"
                    variant="outline"
                    disabled={!playbackUrl}
                    onClick={() => void togglePlayback()}
                  >
                    {playing ? <Pause className="size-5" /> : <Play className="size-5" />}
                    {playing ? "Pause" : "Playback"}
                  </Button>
                  <Button
                    type="button"
                    size="touch"
                    variant="outline"
                    onClick={discardRecording}
                  >
                    <Trash2 className="size-5" />
                    Delete
                  </Button>
                  <Button
                    type="button"
                    size="touch"
                    className="col-span-2"
                    disabled={busy === "upload"}
                    onClick={() => void uploadRecording()}
                  >
                    {busy === "upload" ? "Saving…" : "Save recording"}
                  </Button>
                </>
              ) : null}
            </div>
          </>
        ) : null}

        {step === "review" || step === "interpretation" ? (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={!playbackUrl}
                onClick={() => void togglePlayback()}
              >
                {playing ? <Pause className="size-4" /> : <Play className="size-4" />}
                Playback
              </Button>
              <Button type="button" size="sm" variant="outline" onClick={() => void deleteSavedNote()}>
                <Trash2 className="size-4" />
                Delete
              </Button>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium" htmlFor="audio-note-transcript">
                Transcript
              </label>
              <Textarea
                id="audio-note-transcript"
                rows={5}
                value={transcript}
                onChange={(event) => setTranscript(event.target.value)}
                placeholder="Edit the transcript before saving…"
              />
            </div>

            {step === "review" ? (
              <Button
                type="button"
                size="touch"
                className="w-full"
                disabled={Boolean(busy) || !savedNote}
                onClick={() => void transcribeAndInterpret()}
              >
                {busy === "transcribe" || busy === "interpret"
                  ? "Working…"
                  : "Transcribe and interpret"}
              </Button>
            ) : null}

            {interpretation ? (
              <div className="space-y-4 rounded-xl border border-border bg-card p-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                    Cleaned note
                  </p>
                  <p className="mt-1 text-base leading-relaxed">{interpretation.cleaned_note}</p>
                </div>

                {interpretation.observations.length > 0 ? (
                  <div>
                    <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                      Observations
                    </p>
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
                      {interpretation.observations.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {interpretation.visual_elements.length > 0 ? (
                  <div>
                    <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                      Visual elements
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {interpretation.visual_elements.map((item) => (
                        <Badge key={item} variant="secondary">
                          {item}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ) : null}

                {interpretation.tags.length > 0 ? (
                  <div>
                    <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                      Tags
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {interpretation.tags.map((item) => (
                        <Badge key={item} variant="outline">
                          {item}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ) : null}

                {entityLinks.length > 0 ? (
                  <div>
                    <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                      Related entities
                    </p>
                    <ul className="mt-2 space-y-1 text-sm">
                      {entityLinks.map(({ name, entity }) => (
                        <li key={name}>
                          {entity && visitId ? (
                            <Link
                              href={`/visits/${visitId}`}
                              className="text-primary underline-offset-4 hover:underline"
                            >
                              {name}
                            </Link>
                          ) : (
                            <span>{name}</span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {interpretation.suggested_annotations.length > 0 ? (
                  <div>
                    <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                      Suggested annotations
                    </p>
                    <ul className="mt-2 space-y-2 text-sm">
                      {interpretation.suggested_annotations.map((item, index) => (
                        <li key={`${item.category}-${index}`} className="rounded-lg bg-muted/40 p-3">
                          <p className="font-medium">{item.note}</p>
                          <p className="mt-1 text-xs text-muted-foreground">{item.category}</p>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            ) : null}

            {step === "interpretation" ? (
              <div className="grid gap-2">
                <Button
                  type="button"
                  size="touch"
                  className="w-full"
                  disabled={Boolean(busy)}
                  onClick={() => void savePersonalNote()}
                >
                  {busy === "save-note" ? "Saving…" : "Save as personal note"}
                </Button>
                {artworkId && interpretation?.suggested_annotations?.length ? (
                  <Button
                    type="button"
                    size="touch"
                    variant="outline"
                    className="w-full"
                    disabled={Boolean(busy)}
                    onClick={() => void createSuggestedAnnotations()}
                  >
                    {busy === "annotations"
                      ? "Creating…"
                      : `Create ${interpretation.suggested_annotations.length} suggested annotation${
                          interpretation.suggested_annotations.length === 1 ? "" : "s"
                        }`}
                  </Button>
                ) : null}
              </div>
            ) : null}
          </>
        ) : null}

        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        {success ? <p className="text-sm text-muted-foreground">{success}</p> : null}

        {playbackUrl ? (
          <audio
            ref={audioRef}
            src={playbackUrl}
            className="hidden"
            onEnded={() => setPlaying(false)}
            onPause={() => setPlaying(false)}
          />
        ) : null}
      </div>
    </BottomSheet>
  );
}
