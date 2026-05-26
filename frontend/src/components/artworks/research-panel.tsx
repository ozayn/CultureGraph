"use client";

import { useCallback, useEffect, useState } from "react";

import { AiSuggestedAnnotations } from "@/components/artworks/ai-suggested-annotations";
import { ResearchMetadataApply, extractDraftMetadataHints } from "@/components/artworks/research-metadata-apply";
import { AdminActionsMenu } from "@/components/admin/admin-actions-menu";
import { ConfirmDeleteDialog } from "@/components/admin/confirm-delete-dialog";
import { SignInPrompt } from "@/components/auth/sign-in-prompt";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { parseSuggestedAnnotations } from "@/lib/research-suggestions";
import type { ResearchMetadataHints } from "@/lib/artwork-metadata";
import type { AiSuggestedAnnotation, Annotation, Artwork, CulturalEntity, ResearchDraft, ResearchNote } from "@/lib/types";

interface ResearchPanelProps {
  artwork: Artwork;
  canEdit?: boolean;
  hasImage?: boolean;
  culturalEntities?: CulturalEntity[];
  onReady?: (generate: () => Promise<void>) => void;
  onAnnotationAccepted?: (annotation: Annotation) => void;
  onArtworkUpdated?: (artwork: Artwork) => void;
  onHintsChange?: (hints: ResearchMetadataHints | null) => void;
  onApplyReviewReady?: (openReview: (preset?: "title" | "artist" | "both" | "review") => void) => void;
}

function parseResearchNote(note: ResearchNote): ResearchDraft {
  function parseJsonList(value: string): string[] {
    try {
      const parsed = JSON.parse(value) as unknown;
      return Array.isArray(parsed) ? parsed.map(String) : [];
    } catch {
      return value
        .split("\n")
        .map((item) => item.trim())
        .filter(Boolean);
    }
  }

  return {
    short_summary: note.short_summary,
    historical_context: note.historical_context,
    visual_elements_to_notice: parseJsonList(note.visual_elements_to_notice),
    related_questions: parseJsonList(note.related_questions),
    suggested_annotations: parseSuggestedAnnotations(note.suggested_annotations),
    possible_title: note.possible_title,
    possible_artist: note.possible_artist,
    period_or_movement: note.period_or_movement,
  };
}

export function ResearchPanel({
  artwork,
  canEdit = true,
  hasImage = false,
  culturalEntities = [],
  onReady,
  onAnnotationAccepted,
  onArtworkUpdated,
  onHintsChange,
  onApplyReviewReady,
}: ResearchPanelProps) {
  const artworkId = artwork.id;
  const [notes, setNotes] = useState<ResearchNote[]>([]);
  const [draft, setDraft] = useState<ResearchDraft | null>(null);
  const [visibleSuggestions, setVisibleSuggestions] = useState<AiSuggestedAnnotation[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingNotes, setLoadingNotes] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingNote, setDeletingNote] = useState<ResearchNote | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  function loadDraft(nextDraft: ResearchDraft) {
    setDraft(nextDraft);
    setVisibleSuggestions(nextDraft.suggested_annotations ?? []);
  }

  useEffect(() => {
    let cancelled = false;

    async function fetchNotes() {
      setLoadingNotes(true);
      try {
        const result = await api.get<ResearchNote[]>(`/api/artworks/${artworkId}/research`);
        if (cancelled) return;
        setNotes(result);
        if (result.length > 0) {
          loadDraft(parseResearchNote(result[0]));
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Could not load research notes.");
        }
      } finally {
        if (!cancelled) {
          setLoadingNotes(false);
        }
      }
    }

    void fetchNotes();

    return () => {
      cancelled = true;
    };
  }, [artworkId]);

  const generateDraft = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.post<ResearchDraft>(`/api/artworks/${artworkId}/research`);
      loadDraft(result);
      const saved = await api.get<ResearchNote[]>(`/api/artworks/${artworkId}/research`);
      setNotes(saved);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not generate research.");
    } finally {
      setLoading(false);
    }
  }, [artworkId]);

  useEffect(() => {
    onReady?.(generateDraft);
  }, [generateDraft, onReady]);

  useEffect(() => {
    onHintsChange?.(draft ? extractDraftMetadataHints(draft) : null);
  }, [draft, onHintsChange]);

  async function deleteNote() {
    if (!deletingNote) return;
    setDeleteLoading(true);
    setError(null);
    try {
      await api.delete(`/api/artworks/${artworkId}/research/${deletingNote.id}`);
      setNotes((current) => current.filter((note) => note.id !== deletingNote.id));
      if (notes[0]?.id === deletingNote.id) {
        const remaining = notes.filter((note) => note.id !== deletingNote.id);
        if (remaining[0]) {
          loadDraft(parseResearchNote(remaining[0]));
        } else {
          setDraft(null);
          setVisibleSuggestions([]);
        }
      }
      setDeletingNote(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete research note.");
    } finally {
      setDeleteLoading(false);
    }
  }

  return (
    <section className="space-y-4 rounded-xl border border-border bg-card p-4 sm:p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="font-heading text-lg">Research draft</h3>
          <p className="text-sm text-muted-foreground">
            AI-assisted context and reviewable annotation suggestions.
          </p>
        </div>
        <Button
          onClick={() => void generateDraft()}
          disabled={loading || !canEdit}
          variant="outline"
          size="touch"
          className="w-full sm:w-auto"
        >
          {loading ? "Generating…" : "Research with AI"}
        </Button>
      </div>

      {!canEdit ? <SignInPrompt compact className="mt-2" /> : null}

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {loadingNotes ? (
        <p className="text-sm text-muted-foreground">Loading saved research…</p>
      ) : notes.length > 0 ? (
        <ul className="space-y-2">
          {notes.map((note) => (
            <li
              key={note.id}
              className="flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2 text-sm"
            >
              <button
                type="button"
                className="min-w-0 flex-1 text-left"
                onClick={() => loadDraft(parseResearchNote(note))}
              >
                <span className="block truncate font-medium">{note.short_summary}</span>
                <span className="text-xs text-muted-foreground">
                  {new Date(note.created_at).toLocaleString()}
                </span>
              </button>
              {canEdit ? (
                <AdminActionsMenu
                  label="Research note actions"
                  onDelete={() => setDeletingNote(note)}
                />
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}

      {draft ? (
        <div className="space-y-5 text-base leading-relaxed">
          <ResearchMetadataApply
            artwork={artwork}
            draft={draft}
            canEdit={canEdit}
            onApplied={(updated) => onArtworkUpdated?.(updated)}
            onReviewControlReady={onApplyReviewReady}
          />

          <div>
            <h4 className="mb-1 font-medium">Summary</h4>
            <p className="text-muted-foreground">{draft.short_summary}</p>
          </div>
          <div>
            <h4 className="mb-1 font-medium">Historical context</h4>
            <p className="text-muted-foreground">{draft.historical_context}</p>
          </div>
          <div>
            <h4 className="mb-1 font-medium">Visual elements to notice</h4>
            <ul className="list-disc space-y-2 pl-5 text-muted-foreground">
              {draft.visual_elements_to_notice.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="mb-1 font-medium">Related questions</h4>
            <ul className="list-disc space-y-2 pl-5 text-muted-foreground">
              {draft.related_questions.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <AiSuggestedAnnotations
            artworkId={artworkId}
            suggestions={visibleSuggestions}
            culturalEntities={culturalEntities}
            hasImage={hasImage}
            onSuggestionsChange={setVisibleSuggestions}
            onAnnotationAccepted={onAnnotationAccepted}
          />
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          Tap Research with AI to build a draft of context and connections.
        </p>
      )}

      <ConfirmDeleteDialog
        open={deletingNote !== null}
        onOpenChange={(open) => {
          if (!open) setDeletingNote(null);
        }}
        title="Delete research note?"
        description="This removes the saved AI research draft for this artwork."
        loading={deleteLoading}
        onConfirm={deleteNote}
      />
    </section>
  );
}

