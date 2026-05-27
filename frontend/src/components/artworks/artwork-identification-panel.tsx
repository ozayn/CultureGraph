"use client";

import { EntryThumbnail } from "@/components/ui/entry-thumbnail";
import type { ArtworkIdentification } from "@/lib/types";
import { cn } from "@/lib/utils";

const MODE_LABELS: Record<ArtworkIdentification["identification_mode"], string> = {
  catalog_match: "Collection match",
  possible_match: "Possible matches",
  style_subject: "Style & subject analysis",
};

const CONFIDENCE_STYLES: Record<ArtworkIdentification["confidence_level"], string> = {
  high: "border-emerald-500/40 bg-emerald-500/5 text-emerald-700 dark:text-emerald-300",
  medium: "border-amber-500/40 bg-amber-500/5 text-amber-800 dark:text-amber-200",
  low: "border-border bg-muted/30 text-muted-foreground",
};

interface ArtworkIdentificationPanelProps {
  identification: ArtworkIdentification;
}

function confidenceLabel(level: ArtworkIdentification["confidence_level"]): string {
  if (level === "high") return "High confidence";
  if (level === "medium") return "Moderate confidence";
  return "Low confidence — verify manually";
}

export function ArtworkIdentificationPanel({
  identification,
}: ArtworkIdentificationPanelProps) {
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
    suggested_title,
    suggested_artist,
  } = identification;

  const showExactSuggestion =
    identification_mode === "catalog_match" && (suggested_title || suggested_artist);

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

function CandidatePreview({
  candidate,
  compact = false,
}: {
  candidate: NonNullable<ArtworkIdentification["top_candidate"]>;
  compact?: boolean;
}) {
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
          {candidate.confidence != null
            ? ` · ${Math.round(candidate.confidence * 100)}% match`
            : null}
        </p>
      </div>
    </div>
  );
}
