"use client";

import { Loader2, RefreshCw, Sparkles } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AiSuggestedAnnotations } from "@/components/artworks/ai-suggested-annotations";
import {
  LookupCandidateList,
} from "@/components/artworks/enrichment-lookup-candidates";
import {
  ResearchMetadataApply,
  extractDraftMetadataHints,
} from "@/components/artworks/research-metadata-apply";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { ResearchMetadataHints } from "@/lib/artwork-metadata";
import { parseSuggestedAnnotations } from "@/lib/research-suggestions";
import type {
  AiSuggestedAnnotation,
  Annotation,
  Artwork,
  ArtworkEnrichmentStage,
  ArtworkEnrichmentState,
  CulturalEntity,
  ResearchDraft,
} from "@/lib/types";
import { cn } from "@/lib/utils";

const STAGE_LABELS: Record<ArtworkEnrichmentStage, string> = {
  identifying: "Identifying artwork…",
  searching_collections: "Searching museum collections…",
  generating_annotations: "Generating annotation suggestions…",
};

interface ArtworkEnrichmentPanelProps {
  artwork: Artwork;
  canEdit?: boolean;
  hasImage?: boolean;
  autoFocus?: boolean;
  culturalEntities?: CulturalEntity[];
  onArtworkUpdated?: (artwork: Artwork) => void;
  onAnnotationAccepted?: (annotation: Annotation) => void;
  onHintsChange?: (hints: ResearchMetadataHints | null) => void;
  onApplyReviewReady?: (openReview: () => void) => void;
}

function isActive(status: ArtworkEnrichmentState["status"]): boolean {
  return status === "pending" || status === "running";
}

export function ArtworkEnrichmentPanel({
  artwork,
  canEdit = true,
  hasImage = false,
  autoFocus = false,
  culturalEntities = [],
  onArtworkUpdated,
  onAnnotationAccepted,
  onHintsChange,
  onApplyReviewReady,
}: ArtworkEnrichmentPanelProps) {
  const artworkId = artwork.id;
  const [state, setState] = useState<ArtworkEnrichmentState | null>(null);
  const [suggestions, setSuggestions] = useState<AiSuggestedAnnotation[]>([]);
  const [loading, setLoading] = useState(true);
  const [rerunning, setRerunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revealed, setRevealed] = useState({
    identification: false,
    context: false,
    annotations: false,
    lookup: false,
  });

  const draft = state?.draft ?? null;
  const active = state ? isActive(state.status) : false;

  const stageLabel = useMemo(() => {
    if (!state) return "Analyzing artwork…";
    if (state.stage) return STAGE_LABELS[state.stage];
    if (state.status === "pending") return "Analyzing artwork…";
    if (state.status === "running") return "Analyzing artwork…";
    return null;
  }, [state]);

  const refresh = useCallback(async () => {
    try {
      const next = await api.get<ArtworkEnrichmentState>(
        `/api/artworks/${artworkId}/enrichment`
      );
      setState(next);
      if (next.draft?.suggested_annotations) {
        setSuggestions(next.draft.suggested_annotations);
      }
      setError(next.error);
      return next;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load AI enrichment.");
      return null;
    }
  }, [artworkId]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      const next = await refresh();
      if (!cancelled) setLoading(false);

      if (
        autoFocus &&
        canEdit &&
        hasImage &&
        next &&
        next.status === "idle" &&
        !cancelled
      ) {
        try {
          await api.post(`/api/artworks/${artworkId}/enrichment`);
          if (!cancelled) await refresh();
        } catch {
          // Upload handler may have already queued enrichment.
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [artworkId, autoFocus, canEdit, hasImage, refresh]);

  useEffect(() => {
    if (!state || isActive(state.status)) return;

    const timers = [
      window.setTimeout(() => setRevealed((current) => ({ ...current, identification: true })), 80),
      window.setTimeout(() => setRevealed((current) => ({ ...current, context: true })), 220),
      window.setTimeout(() => setRevealed((current) => ({ ...current, annotations: true })), 360),
      window.setTimeout(() => setRevealed((current) => ({ ...current, lookup: true })), 500),
    ];

    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [state?.status, state?.draft?.short_summary]);

  useEffect(() => {
    if (!active) return;

    const interval = window.setInterval(() => {
      void refresh();
    }, 1500);

    return () => window.clearInterval(interval);
  }, [active, refresh]);

  useEffect(() => {
    onHintsChange?.(draft ? extractDraftMetadataHints(draft) : null);
  }, [draft, onHintsChange]);

  async function rerunEnrichment() {
    setRerunning(true);
    setError(null);
    setRevealed({
      identification: false,
      context: false,
      annotations: false,
      lookup: false,
    });
    try {
      await api.post(`/api/artworks/${artworkId}/enrichment`);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not restart AI enrichment.");
    } finally {
      setRerunning(false);
    }
  }

  async function persistSuggestions(next: AiSuggestedAnnotation[]) {
    if (!state?.research_note_id) return;
    const saved = await api.patch<{ suggested_annotations: AiSuggestedAnnotation[] }>(
      `/api/artworks/${artworkId}/research/${state.research_note_id}/suggestions`,
      { suggested_annotations: next }
    );
    setSuggestions(saved.suggested_annotations);
    setState((current) =>
      current && current.draft
        ? {
            ...current,
            draft: { ...current.draft, suggested_annotations: saved.suggested_annotations },
          }
        : current
    );
  }

  const showAmbientHeader = active || draft || loading;

  return (
    <section
      className="space-y-4 rounded-xl border border-border bg-card p-4 sm:p-5"
      aria-live="polite"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Sparkles className="size-4" aria-hidden />
          </div>
          <div>
            <h3 className="font-heading text-lg">AI assistant</h3>
            <p className="text-sm text-muted-foreground">
              Identification, context, and collection matches as you capture.
            </p>
          </div>
        </div>
        {canEdit && hasImage ? (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="min-h-9 self-start text-muted-foreground"
            disabled={active || rerunning}
            onClick={() => void rerunEnrichment()}
          >
            <RefreshCw className={cn("mr-1.5 size-3.5", rerunning && "animate-spin")} />
            Run AI again
          </Button>
        ) : null}
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {active || rerunning ? (
        <div className="flex items-center gap-2 rounded-lg border border-dashed border-primary/30 bg-primary/5 px-3 py-3 text-sm text-foreground">
          <Loader2 className="size-4 shrink-0 animate-spin text-primary" aria-hidden />
          <span>{stageLabel ?? "Analyzing artwork…"}</span>
        </div>
      ) : null}

      {!hasImage && !loading ? (
        <p className="text-sm text-muted-foreground">
          Add a photo to start automatic AI enrichment.
        </p>
      ) : null}

      {loading && !draft && !active ? (
        <p className="text-sm text-muted-foreground">Loading AI results…</p>
      ) : null}

      {draft && revealed.identification ? (
        <div
          className={cn(
            "space-y-3 rounded-lg border border-border/80 bg-muted/20 p-4 transition-all duration-500",
            showAmbientHeader ? "animate-in fade-in slide-in-from-bottom-2" : ""
          )}
        >
          <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
            Suggested identification
          </p>
          <ResearchMetadataApply
            artwork={artwork}
            draft={draft}
            canEdit={canEdit}
            onApplied={(updated) => onArtworkUpdated?.(updated)}
            onReviewControlReady={onApplyReviewReady}
          />
        </div>
      ) : null}

      {draft && revealed.context ? (
        <div className="space-y-4 text-base leading-relaxed animate-in fade-in slide-in-from-bottom-2 duration-500">
          {draft.period_or_movement ? (
            <div>
              <h4 className="mb-1 text-sm font-medium">Style / movement</h4>
              <p className="text-muted-foreground">{draft.period_or_movement}</p>
            </div>
          ) : null}
          <div>
            <h4 className="mb-1 text-sm font-medium">Summary</h4>
            <p className="text-muted-foreground">{draft.short_summary}</p>
          </div>
          <div>
            <h4 className="mb-1 text-sm font-medium">Historical context</h4>
            <p className="text-muted-foreground">{draft.historical_context}</p>
          </div>
          {draft.visual_elements_to_notice.length > 0 ? (
            <div>
              <h4 className="mb-1 text-sm font-medium">Visual elements to notice</h4>
              <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
                {draft.visual_elements_to_notice.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}

      {draft && revealed.annotations && suggestions.length > 0 ? (
        <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
          <AiSuggestedAnnotations
            artworkId={artworkId}
            suggestions={suggestions}
            culturalEntities={culturalEntities}
            hasImage={hasImage}
            onSuggestionsChange={setSuggestions}
            onPersistSuggestions={canEdit ? persistSuggestions : undefined}
            onAnnotationAccepted={onAnnotationAccepted}
          />
        </div>
      ) : null}

      {state?.lookup && revealed.lookup ? (
        <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
          <LookupCandidateList
            artwork={artwork}
            lookup={state.lookup}
            canEdit={canEdit}
            onApplied={(updated) => onArtworkUpdated?.(updated)}
          />
        </div>
      ) : null}

      {!active && !loading && !draft && hasImage && state?.status === "idle" ? (
        <p className="text-sm text-muted-foreground">
          AI enrichment has not run yet for this artwork.
        </p>
      ) : null}
    </section>
  );
}

export function enrichmentDraftFromNote(note: {
  short_summary: string;
  historical_context: string;
  visual_elements_to_notice: string;
  related_questions: string;
  suggested_annotations: string;
  possible_title?: string | null;
  possible_artist?: string | null;
  period_or_movement?: string | null;
}): ResearchDraft {
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
