"use client";

import { useState } from "react";

import { useArtworkImageLookup } from "@/components/artworks/artwork-image-lookup-panel";
import { EntryThumbnail } from "@/components/ui/entry-thumbnail";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { isPlaceholderTitle } from "@/lib/artwork-metadata";
import type { Artwork, ArtworkIdentification } from "@/lib/types";
import { cn } from "@/lib/utils";

const MODE_LABELS: Record<ArtworkIdentification["identification_mode"], string> = {
  catalog_match: "Collection match",
  possible_match: "Related / possible matches",
  style_subject: "Style & subject analysis",
};

const CONFIDENCE_STYLES: Record<ArtworkIdentification["confidence_level"], string> = {
  high: "border-emerald-500/40 bg-emerald-500/5 text-emerald-700 dark:text-emerald-300",
  medium: "border-amber-500/40 bg-amber-500/5 text-amber-800 dark:text-amber-200",
  low: "border-border bg-muted/30 text-muted-foreground",
};

interface ArtworkIdentificationPanelProps {
  identification: ArtworkIdentification;
  artwork?: Artwork;
  canEdit?: boolean;
  onArtworkUpdated?: (artwork: Artwork) => void;
}

function confidenceLabel(level: ArtworkIdentification["confidence_level"]): string {
  if (level === "high") return "Verified identity";
  if (level === "medium") return "Strong probable match";
  return "Visually similar — verify manually";
}

function formatPercent(value: number | null | undefined): string | null {
  if (value == null) return null;
  return `${Math.round(value * 100)}%`;
}

export function ArtworkIdentificationPanel({
  identification,
  artwork,
  canEdit = false,
  onArtworkUpdated,
}: ArtworkIdentificationPanelProps) {
  const { openLookup } = useArtworkImageLookup();
  const [savingWorkingTitle, setSavingWorkingTitle] = useState(false);
  const [workingTitleError, setWorkingTitleError] = useState<string | null>(null);

  const {
    identification_mode,
    confidence_level,
    display_summary,
    style_assessment,
    subject_assessment,
    iconography_notes = [],
    top_candidate,
    alternative_matches = [],
    match_reasons = [],
    match_explanation,
    uncertainty_notes = [],
    identity_certainty,
    visual_similarity,
    suggested_title,
    suggested_artist,
    visual_hypothesis_title,
    visual_hypothesis_artist,
    visual_hypothesis_confidence,
    visual_hypothesis_reason,
  } = identification;

  const showExactSuggestion =
    identification_mode === "catalog_match" && (suggested_title || suggested_artist);

  const showVisualHypothesis =
    identification_mode !== "catalog_match" &&
    Boolean(visual_hypothesis_title || visual_hypothesis_artist);

  async function useWorkingTitle() {
    if (!artwork || !canEdit) return;
    const title = visual_hypothesis_title?.trim();
    if (!title) return;

    setSavingWorkingTitle(true);
    setWorkingTitleError(null);
    try {
      const payload: Partial<Artwork> = { title };
      if (visual_hypothesis_artist?.trim()) {
        payload.artist = visual_hypothesis_artist.trim();
      }
      const updated = await api.put<Artwork>(`/api/artworks/${artwork.id}`, payload);
      onArtworkUpdated?.(updated);
    } catch (error) {
      setWorkingTitleError(
        error instanceof Error ? error.message : "Could not save working title."
      );
    } finally {
      setSavingWorkingTitle(false);
    }
  }

  function searchCollectionsWithHypothesis() {
    if (!visual_hypothesis_title && !visual_hypothesis_artist) return;
    openLookup({
      title: visual_hypothesis_title ?? undefined,
      artist: visual_hypothesis_artist ?? undefined,
    });
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
          {MODE_LABELS[identification_mode]}
        </span>
        <span
          className={cn(
            "rounded-full border px-2 py-0.5 text-xs font-medium",
            CONFIDENCE_STYLES[confidence_level]
          )}
        >
          {confidenceLabel(confidence_level)}
        </span>
      </div>

      <p className="text-sm leading-relaxed text-foreground">{display_summary}</p>

      {(identity_certainty != null || visual_similarity != null) && identification_mode !== "style_subject" ? (
        <dl className="grid gap-2 text-xs sm:grid-cols-2">
          {identity_certainty != null ? (
            <div>
              <dt className="font-medium text-muted-foreground">Identity certainty</dt>
              <dd>{formatPercent(identity_certainty)}</dd>
            </div>
          ) : null}
          {visual_similarity != null ? (
            <div>
              <dt className="font-medium text-muted-foreground">Visual similarity</dt>
              <dd>{formatPercent(visual_similarity)}</dd>
            </div>
          ) : null}
        </dl>
      ) : null}

      {match_explanation ? (
        <p className="rounded-lg border border-border/80 bg-muted/20 px-3 py-2 text-sm leading-relaxed text-muted-foreground">
          {match_explanation}
        </p>
      ) : null}

      {uncertainty_notes.length > 0 ? (
        <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
          {uncertainty_notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      ) : null}

      {showExactSuggestion ? (
        <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 px-3 py-2 text-sm">
          {suggested_title ? (
            <p>
              <span className="text-muted-foreground">Catalog title: </span>
              <span className="font-medium">{suggested_title}</span>
            </p>
          ) : null}
          {suggested_artist ? (
            <p>
              <span className="text-muted-foreground">Artist: </span>
              <span className="font-medium">{suggested_artist}</span>
            </p>
          ) : null}
        </div>
      ) : null}

      {showVisualHypothesis ? (
        <div className="space-y-3 rounded-lg border border-sky-500/30 bg-sky-500/5 px-3 py-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-xs font-medium uppercase tracking-[0.14em] text-sky-800 dark:text-sky-200">
              AI visual hypothesis
            </p>
            {visual_hypothesis_confidence != null ? (
              <span className="rounded-full border border-sky-500/30 px-2 py-0.5 text-[11px] text-sky-900 dark:text-sky-100">
                {formatPercent(visual_hypothesis_confidence)} confidence
              </span>
            ) : null}
          </div>
          {visual_hypothesis_title ? (
            <p>
              <span className="text-muted-foreground">Title: </span>
              <span className="font-medium">{visual_hypothesis_title}</span>
            </p>
          ) : null}
          {visual_hypothesis_artist ? (
            <p>
              <span className="text-muted-foreground">Artist: </span>
              <span className="font-medium">{visual_hypothesis_artist}</span>
            </p>
          ) : null}
          {visual_hypothesis_reason ? (
            <p className="text-xs leading-relaxed text-muted-foreground">{visual_hypothesis_reason}</p>
          ) : null}
          <p className="text-xs text-muted-foreground">
            Not verified against collection records.
          </p>
          {canEdit && artwork ? (
            <div className="flex flex-col gap-2 sm:flex-row">
              {visual_hypothesis_title && isPlaceholderTitle(artwork.title) ? (
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="min-h-9"
                  disabled={savingWorkingTitle}
                  onClick={() => void useWorkingTitle()}
                >
                  {savingWorkingTitle ? "Saving…" : "Use as working title"}
                </Button>
              ) : null}
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="min-h-9"
                onClick={searchCollectionsWithHypothesis}
              >
                Search collections with this title
              </Button>
            </div>
          ) : null}
          {workingTitleError ? (
            <p className="text-xs text-destructive">{workingTitleError}</p>
          ) : null}
        </div>
      ) : null}

      {(style_assessment || subject_assessment) && !showExactSuggestion ? (
        <dl className="grid gap-2 text-sm sm:grid-cols-2">
          {style_assessment ? (
            <div>
              <dt className="text-xs font-medium text-muted-foreground">Style / movement</dt>
              <dd>{style_assessment}</dd>
            </div>
          ) : null}
          {subject_assessment ? (
            <div>
              <dt className="text-xs font-medium text-muted-foreground">Subject</dt>
              <dd>{subject_assessment}</dd>
            </div>
          ) : null}
        </dl>
      ) : null}

      {iconography_notes.length > 0 ? (
        <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
          {iconography_notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      ) : null}

      {match_reasons.length > 0 ? (
        <div>
          <p className="mb-1 text-xs font-medium text-muted-foreground">Why it matched</p>
          <ul className="flex flex-wrap gap-1.5">
            {match_reasons.map((reason) => (
              <li
                key={reason}
                className="rounded-md border border-border bg-background px-2 py-0.5 text-xs text-muted-foreground"
              >
                {reason}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {top_candidate ? (
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">Top candidate</p>
          <CandidatePreview candidate={top_candidate} />
        </div>
      ) : null}

      {alternative_matches.length > 0 ? (
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">Alternative matches</p>
          <ul className="space-y-2">
            {alternative_matches.map((candidate) => (
              <li key={candidate.external_id ?? candidate.object_url ?? candidate.title}>
                <CandidatePreview candidate={candidate} compact />
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function candidateRelationLabel(
  candidate: NonNullable<ArtworkIdentification["top_candidate"]>
): string {
  const identity = candidate.identity_certainty ?? candidate.confidence;
  if (candidate.match_tier === "high" && identity >= 0.95) {
    return "Verified match";
  }
  if (identity >= 0.8) {
    return "Strong probable match";
  }
  if ((candidate.visual_similarity ?? 0) >= 0.35) {
    return "Visually similar";
  }
  return "Related work";
}

function CandidatePreview({
  candidate,
  compact = false,
}: {
  candidate: NonNullable<ArtworkIdentification["top_candidate"]>;
  compact?: boolean;
}) {
  const identity = candidate.identity_certainty ?? candidate.confidence;
  const visual = candidate.visual_similarity;

  return (
    <div
      className={cn(
        "flex gap-3 rounded-lg border border-border bg-card p-2",
        compact && "text-sm"
      )}
    >
      <EntryThumbnail
        imageUrl={candidate.image_thumbnail_url ?? candidate.image_url}
        alt={candidate.title}
        className="size-14 shrink-0 rounded-md"
      />
      <div className="min-w-0 flex-1">
        <p className="font-medium leading-snug">{candidate.title}</p>
        {candidate.artist ? (
          <p className="text-xs text-muted-foreground">{candidate.artist}</p>
        ) : null}
        <p className="text-xs text-muted-foreground">
          {candidate.source_name}
          {identity != null ? ` · identity ${Math.round(identity * 100)}%` : null}
          {visual != null ? ` · visual ${Math.round(visual * 100)}%` : null}
        </p>
        <p className="text-[11px] text-muted-foreground">{candidateRelationLabel(candidate)}</p>
        {candidate.match_explanation ? (
          <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
            {candidate.match_explanation}
          </p>
        ) : null}
      </div>
    </div>
  );
}
