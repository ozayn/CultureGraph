"use client";

import { useCallback, useEffect, useState } from "react";

import { AdminActionsMenu } from "@/components/admin/admin-actions-menu";
import { ConfirmDeleteDialog } from "@/components/admin/confirm-delete-dialog";
import { SignInPrompt } from "@/components/auth/sign-in-prompt";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { ResearchDraft, ResearchNote } from "@/lib/types";

interface ResearchPanelProps {
  artworkId: number;
  canEdit?: boolean;
  onReady?: (generate: () => Promise<void>) => void;
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

  function parseSuggested(value: string): ResearchDraft["suggested_annotations"] {
    try {
      const parsed = JSON.parse(value) as unknown;
      if (Array.isArray(parsed)) {
        return parsed.map((item) => {
          if (typeof item === "object" && item !== null && "category" in item && "text" in item) {
            return {
              category: String((item as { category: unknown }).category),
              text: String((item as { text: unknown }).text),
            };
          }
          return { category: "observation", text: String(item) };
        });
      }
    } catch {
      // fall through to line parsing
    }

    return value
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const [category, ...rest] = line.split(" — ");
        return {
          category: category || "observation",
          text: rest.join(" — ") || line,
        };
      });
  }

  return {
    short_summary: note.short_summary,
    historical_context: note.historical_context,
    visual_elements_to_notice: parseJsonList(note.visual_elements_to_notice),
    related_questions: parseJsonList(note.related_questions),
    suggested_annotations: parseSuggested(note.suggested_annotations),
  };
}

export function ResearchPanel({ artworkId, canEdit = true, onReady }: ResearchPanelProps) {
  const [notes, setNotes] = useState<ResearchNote[]>([]);
  const [draft, setDraft] = useState<ResearchDraft | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingNotes, setLoadingNotes] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingNote, setDeletingNote] = useState<ResearchNote | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const loadNotes = useCallback(async () => {
    setLoadingNotes(true);
    try {
      const result = await api.get<ResearchNote[]>(`/api/artworks/${artworkId}/research`);
      setNotes(result);
      if (result.length > 0) {
        setDraft(parseResearchNote(result[0]));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load research notes.");
    } finally {
      setLoadingNotes(false);
    }
  }, [artworkId]);

  useEffect(() => {
    void loadNotes();
  }, [loadNotes]);

  const generateDraft = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.post<ResearchDraft>(
        `/api/artworks/${artworkId}/research`
      );
      setDraft(result);
      await loadNotes();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not generate research.");
    } finally {
      setLoading(false);
    }
  }, [artworkId, loadNotes]);

  useEffect(() => {
    onReady?.(generateDraft);
  }, [generateDraft, onReady]);

  async function deleteNote() {
    if (!deletingNote) return;
    setDeleteLoading(true);
    setError(null);
    try {
      await api.delete(`/api/artworks/${artworkId}/research/${deletingNote.id}`);
      setNotes((current) => current.filter((note) => note.id !== deletingNote.id));
      if (notes[0]?.id === deletingNote.id) {
        const remaining = notes.filter((note) => note.id !== deletingNote.id);
        setDraft(remaining[0] ? parseResearchNote(remaining[0]) : null);
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
            AI-assisted context (mocked for now).
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
                onClick={() => setDraft(parseResearchNote(note))}
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
          <div>
            <h4 className="mb-1 font-medium">Suggested annotations</h4>
            <ul className="space-y-2">
              {draft.suggested_annotations.map((item) => (
                <li
                  key={`${item.category}-${item.text}`}
                  className="rounded-lg bg-muted/50 px-3 py-3 text-muted-foreground"
                >
                  <span className="font-medium text-foreground">{item.category}</span>
                  {" — "}
                  {item.text}
                </li>
              ))}
            </ul>
          </div>
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
