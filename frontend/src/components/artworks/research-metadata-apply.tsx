"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { useArtworkImageLookup } from "@/components/artworks/artwork-image-lookup-panel";
import { api } from "@/lib/api";
import {
  buildYearPeriodValue,
  defaultMetadataFieldChecked,
  extractResearchMetadataHints,
  formatMetadataCurrent,
  isPlaceholderArtist,
  isPlaceholderNotes,
  isPlaceholderTitle,
  type ResearchMetadataHints,
} from "@/lib/artwork-metadata";
import type { Artwork, ResearchDraft } from "@/lib/types";
import { cn } from "@/lib/utils";

type MetadataFieldKey = "title" | "artist" | "year" | "period" | "medium" | "notes";

interface ApplyFields {
  title: boolean;
  artist: boolean;
  year: boolean;
  period: boolean;
  medium: boolean;
  notes: boolean;
}

interface MetadataRow {
  key: MetadataFieldKey;
  label: string;
  current: string;
  suggested: string;
}

interface ResearchMetadataApplyProps {
  artwork: Artwork;
  draft: ResearchDraft;
  canEdit: boolean;
  onApplied: (artwork: Artwork) => void;
  onReviewControlReady?: (openReview: () => void) => void;
}

function defaultFields(artwork: Artwork, hints: ResearchMetadataHints): ApplyFields {
  const confidence = hints.confidence;
  return {
    title: defaultMetadataFieldChecked(
      artwork.title,
      hints.title,
      confidence,
      isPlaceholderTitle
    ),
    artist: defaultMetadataFieldChecked(
      artwork.artist,
      hints.artist,
      confidence,
      isPlaceholderArtist
    ),
    year: defaultMetadataFieldChecked(
      artwork.year_period,
      hints.year,
      confidence,
      (value) => !value?.trim()
    ),
    period: defaultMetadataFieldChecked(
      artwork.year_period,
      hints.period,
      confidence,
      (value) => !value?.trim()
    ),
    medium: defaultMetadataFieldChecked(
      artwork.medium,
      hints.medium,
      confidence,
      (value) => !value?.trim()
    ),
    notes: defaultMetadataFieldChecked(
      artwork.personal_notes,
      hints.notes,
      confidence,
      isPlaceholderNotes
    ),
  };
}

export function extractDraftMetadataHints(draft: ResearchDraft): ResearchMetadataHints | null {
  return extractResearchMetadataHints({
    possible_title: draft.possible_title,
    possible_artist: draft.possible_artist,
    period_or_movement: draft.period_or_movement,
    confidence: draft.confidence,
    short_summary: draft.short_summary,
    historical_context: draft.historical_context,
    suggested_annotations: draft.suggested_annotations,
  });
}

function buildMetadataRows(artwork: Artwork, hints: ResearchMetadataHints): MetadataRow[] {
  const rows: MetadataRow[] = [];

  if (hints.title) {
    rows.push({
      key: "title",
      label: "Title",
      current: formatMetadataCurrent(artwork.title, "Unknown"),
      suggested: hints.title,
    });
  }
  if (hints.artist) {
    rows.push({
      key: "artist",
      label: "Artist",
      current: formatMetadataCurrent(artwork.artist, "Unknown"),
      suggested: hints.artist,
    });
  }
  if (hints.year) {
    rows.push({
      key: "year",
      label: "Year / date",
      current: formatMetadataCurrent(artwork.year_period),
      suggested: hints.year,
    });
  }
  if (hints.period) {
    rows.push({
      key: "period",
      label: "Period / movement",
      current: formatMetadataCurrent(artwork.year_period),
      suggested: hints.period,
    });
  }
  if (hints.medium) {
    rows.push({
      key: "medium",
      label: "Medium",
      current: formatMetadataCurrent(artwork.medium),
      suggested: hints.medium,
    });
  }
  if (hints.notes) {
    rows.push({
      key: "notes",
      label: "Notes / context",
      current: formatMetadataCurrent(artwork.personal_notes, "None"),
      suggested: hints.notes,
    });
  }

  return rows;
}

export function ResearchMetadataApply({
  artwork,
  draft,
  canEdit,
  onApplied,
  onReviewControlReady,
}: ResearchMetadataApplyProps) {
  const { openLookup, hasImage } = useArtworkImageLookup();
  const hints = extractDraftMetadataHints(draft);
  const rows = useMemo(
    () => (hints ? buildMetadataRows(artwork, hints) : []),
    [artwork, hints]
  );

  const [reviewing, setReviewing] = useState(false);
  const [fields, setFields] = useState<ApplyFields>({
    title: false,
    artist: false,
    year: false,
    period: false,
    medium: false,
    notes: false,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  function openReview() {
    if (!hints) return;
    setSuccess(false);
    setError(null);
    setReviewing(true);
    setFields(defaultFields(artwork, hints));
  }

  useEffect(() => {
    if (!onReviewControlReady || !hints) return;
    onReviewControlReady(openReview);
  }, [onReviewControlReady, hints, artwork]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!canEdit || !hints || rows.length === 0) return null;

  const showTitleHint = Boolean(hints.title) && isPlaceholderTitle(artwork.title);
  const lookupLabel = hasImage ? "Search museum collections" : "Find official image";

  function cancelReview() {
    setReviewing(false);
  }

  function toggleField(key: MetadataFieldKey) {
    setFields((current) => ({ ...current, [key]: !current[key] }));
  }

  async function confirmApply() {
    if (!hints) return;

    const payload: Partial<Artwork> = {};
    if (fields.title && hints.title) payload.title = hints.title;
    if (fields.artist && hints.artist) payload.artist = hints.artist;

    const yearPeriod = buildYearPeriodValue(
      hints.year,
      hints.period,
      fields.year,
      fields.period
    );
    if (yearPeriod) payload.year_period = yearPeriod;

    if (fields.medium && hints.medium) payload.medium = hints.medium;
    if (fields.notes && hints.notes) payload.personal_notes = hints.notes;

    if (!Object.keys(payload).length) return;

    setSaving(true);
    setError(null);
    try {
      const updated = await api.put<Artwork>(`/api/artworks/${artwork.id}`, payload);
      onApplied(updated);
      setSuccess(true);
      setReviewing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update artwork.");
    } finally {
      setSaving(false);
    }
  }

  const hasSelection = Object.values(fields).some(Boolean);

  return (
    <div className="space-y-3 rounded-xl border border-border bg-muted/20 p-3">
      <div className="space-y-1">
        <h4 className="text-sm font-medium">Suggested metadata</h4>
        {hints.confidence != null ? (
          <p className="text-xs text-muted-foreground">
            AI confidence: {Math.round(hints.confidence * 100)}%
            {hints.confidence < 0.55 ? " · review carefully" : null}
          </p>
        ) : null}
        {showTitleHint && hints.title ? (
          <p className="text-xs text-muted-foreground">
            AI suggested title:{" "}
            <span className="font-medium text-foreground">{hints.title}</span>
          </p>
        ) : null}
      </div>

      {!reviewing && !success ? (
        <Button
          type="button"
          size="sm"
          className="min-h-9 w-full sm:w-auto"
          disabled={saving}
          data-testid="research-review-metadata"
          onClick={openReview}
        >
          Review suggested metadata
        </Button>
      ) : null}

      {reviewing ? (
        <div className="space-y-3 rounded-lg border border-border bg-card p-3">
          <p className="text-sm font-medium">Review before saving</p>
          <p className="text-xs text-muted-foreground">
            Checked fields will update the artwork. Existing values stay unless you select them.
          </p>

          <ul className="space-y-2">
            {rows.map((row) => (
              <li
                key={row.key}
                className={cn(
                  "rounded-lg border px-3 py-2",
                  fields[row.key] ? "border-primary/40 bg-primary/5" : "border-border"
                )}
              >
                <label className="flex cursor-pointer items-start gap-3">
                  <input
                    type="checkbox"
                    className="mt-0.5 size-4 shrink-0 accent-primary"
                    checked={fields[row.key]}
                    disabled={saving}
                    onChange={() => toggleField(row.key)}
                  />
                  <span className="min-w-0 flex-1 space-y-1">
                    <span className="block text-xs font-medium">{row.label}</span>
                    <span className="block text-xs leading-relaxed text-muted-foreground">
                      <span className="line-through">{row.current}</span>
                      {" → "}
                      <span className="font-medium text-foreground">{row.suggested}</span>
                    </span>
                  </span>
                </label>
              </li>
            ))}
          </ul>

          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="min-h-9 flex-1"
              disabled={saving}
              onClick={cancelReview}
            >
              Cancel
            </Button>
            <Button
              type="button"
              size="sm"
              className="min-h-9 flex-1"
              disabled={saving || !hasSelection}
              onClick={() => void confirmApply()}
            >
              {saving ? "Saving…" : "Apply selected"}
            </Button>
          </div>
        </div>
      ) : null}

      {success ? (
        <div className="space-y-2 rounded-lg border border-primary/20 bg-primary/5 px-3 py-2">
          <p className="text-xs font-medium text-primary">Artwork metadata updated.</p>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            className="min-h-9 w-full sm:w-auto"
            onClick={openLookup}
          >
            {lookupLabel}
          </Button>
        </div>
      ) : null}

      {error ? <p className="text-xs text-destructive">{error}</p> : null}
    </div>
  );
}
