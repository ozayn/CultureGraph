"use client";

import { Loader2, RefreshCw, Sparkles } from "lucide-react";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { AiSuggestedAnnotations } from "@/components/artworks/ai-suggested-annotations";
import {
  LookupCandidateList,
} from "@/components/artworks/enrichment-lookup-candidates";
import { ArtworkIdentificationPanel } from "@/components/artworks/artwork-identification-panel";
import {
  ResearchMetadataApply,
  extractDraftMetadataHints,
} from "@/components/artworks/research-metadata-apply";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { ResearchMetadataHints } from "@/lib/artwork-metadata";
import { parseSuggestedAnnotations } from "@/lib/research-suggestions";
import { useArtworkEnrichment } from "@/lib/use-artwork-enrichment";
import type {
  AiSuggestedAnnotation,
  Annotation,
  Artwork,
  ArtworkEnrichmentStage,
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
  const pathname = usePathname();
  const pollEnabled = pathname === `/artworks/${artworkId}`;
  const {
    state,
    loading,
    error,
    isActive: active,
    startEnrichment,
  } = useArtworkEnrichment({
    artworkId,
    enabled: pollEnabled,
  });
  const [suggestions, setSuggestions] = useState<AiSuggestedAnnotation[]>([]);
  const [rerunning, setRerunning] = useState(false);
  const autoStartedRef = useRef(false);
  const [revealed, setRevealed] = useState({
    identification: false,
    context: false,
    annotations: false,
    lookup: false,
  });

  const draft = state?.draft ?? null;
  const metadataHints = useMemo(
    () => (draft ? extractDraftMetadataHints(draft, state?.identification ?? null) : null),
    [draft, state?.identification]
  );

  const stageLabel = useMemo(() => {
    if (!state) return "Analyzing artwork…";
    if (state.stage) return STAGE_LABELS[state.stage];
    if (state.status === "pending") return "Analyzing artwork…";
    if (state.status === "running") return "Analyzing artwork…";
    return null;
  }, [state]);

  useEffect(() => {
    if (state?.draft?.suggested_annotations) {
      setSuggestions(state.draft.suggested_annotations);
    }
  }, [state?.draft?.suggested_annotations]);

  useEffect(() => {
    autoStartedRef.current = false;
  }, [artworkId]);

  useEffect(() => {
    if (autoStartedRef.current) return;
    if (!autoFocus || !canEdit || !hasImage || loading || !state || state.status !== "idle") {
      return;
    }

    autoStartedRef.current = true;
    void startEnrichment();
  }, [autoFocus, canEdit, hasImage, loading, state, startEnrichment]);

  useEffect(() => {
    if (!state || active) return;

    const timers = [
      window.setTimeout(() => setRevealed((current) => ({ ...current, identification: true })), 80),
      window.setTimeout(() => setRevealed((current) => ({ ...current, context: true })), 220),
      window.setTimeout(() => setRevealed((current) => ({ ...current, annotations: true })), 360),
      window.setTimeout(() => setRevealed((current) => ({ ...current, lookup: true })), 500),
    ];

    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [active, state?.status, state?.draft?.short_summary]);

  useEffect(() => {
    onHintsChange?.(metadataHints);
  }, [metadataHints, onHintsChange]);

  async function rerunEnrichment() {
    setRerunning(true);
    setRevealed({
      identification: false,
      context: false,
      annotations: false,
      lookup: false,
    });
    try {
      await startEnrichment();
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
    // Local suggestion edits stay in panel state; next enrichment refresh will reconcile.
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
              Visual analysis, retrieval-assisted identification, and collection matches.
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

      {state?.identification && revealed.identification ? (
        <div
          className={cn(
            "space-y-3 rounded-lg border border-border/80 bg-muted/20 p-4 transition-all duration-500",
            showAmbientHeader ? "animate-in fade-in slide-in-from-bottom-2" : ""
          )}
        >
          <ArtworkIdentificationPanel identification={state.identification} />
        </div>
      ) : draft && revealed.identification ? (
        <div
          className={cn(
            "space-y-3 rounded-lg border border-border/80 bg-muted/20 p-4 transition-all duration-500",
            showAmbientHeader ? "animate-in fade-in slide-in-from-bottom-2" : ""
          )}
        >
          <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
            Visual analysis
          </p>
          <p className="text-sm leading-relaxed text-foreground">{draft.short_summary}</p>
        </div>
      ) : null}

      {draft && revealed.identification && metadataHints ? (
        <div className="space-y-3 rounded-lg border border-border/80 bg-muted/20 p-4">
          <ResearchMetadataApply
            artwork={artwork}
            draft={draft}
            identification={state?.identification ?? null}
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
            identification={state.identification ?? null}
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
