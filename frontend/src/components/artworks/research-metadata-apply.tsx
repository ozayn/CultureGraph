"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import {
  cleanAiArtist,
  cleanAiPeriod,
  cleanAiTitle,
  extractResearchMetadataHints,
  isPlaceholderArtist,
  isPlaceholderTitle,
  type ResearchMetadataHints,
} from "@/lib/artwork-metadata";
import type { Artwork, ResearchDraft } from "@/lib/types";
import { cn } from "@/lib/utils";

type ApplyPreset = "title" | "artist" | "both" | "review";

interface ApplyFields {
  title: boolean;
  artist: boolean;
  period: boolean;
}

interface ResearchMetadataApplyProps {
  artwork: Artwork;
  draft: ResearchDraft;
  canEdit: boolean;
  onApplied: (artwork: Artwork) => void;
  onReviewControlReady?: (openReview: (preset?: ApplyPreset) => void) => void;
}

function defaultFields(
  artwork: Artwork,
  hints: ResearchMetadataHints,
  preset: ApplyPreset
): ApplyFields {
  return {
    title:
      preset === "title" ||
      preset === "both" ||
      (preset === "review" && Boolean(hints.title) && isPlaceholderTitle(artwork.title)),
    artist:
      preset === "artist" ||
      preset === "both" ||
      (preset === "review" &&
        Boolean(hints.artist) &&
        isPlaceholderArtist(artwork.artist)),
    period:
      preset === "review" &&
      Boolean(hints.period) &&
      !(artwork.year_period ?? "").trim(),
  };
}

export function extractDraftMetadataHints(draft: ResearchDraft): ResearchMetadataHints | null {
  return extractResearchMetadataHints({
    possible_title: cleanAiTitle(draft.possible_title),
    possible_artist: cleanAiArtist(draft.possible_artist),
    period_or_movement: cleanAiPeriod(draft.period_or_movement),
    confidence: draft.confidence,
    short_summary: draft.short_summary,
  });
}

export function ResearchMetadataApply({
  artwork,
  draft,
  canEdit,
  onApplied,
  onReviewControlReady,
}: ResearchMetadataApplyProps) {
  const hints = extractDraftMetadataHints(draft);

  const [pendingPreset, setPendingPreset] = useState<ApplyPreset | null>(null);
  const [fields, setFields] = useState<ApplyFields>({
    title: false,
    artist: false,
    period: false,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  function startReview(preset: ApplyPreset) {
    setSuccess(null);
    setError(null);
    setPendingPreset(preset);
    setFields(defaultFields(artwork, hints!, preset));
  }

  useEffect(() => {
    if (!onReviewControlReady || !hints) return;
    onReviewControlReady((preset = "review") => startReview(preset));
  }, [onReviewControlReady, hints, artwork]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!canEdit || !hints) return null;

  function cancelReview() {
    setPendingPreset(null);
  }

  const showTitleSuggestion =
    Boolean(hints.title) && isPlaceholderTitle(artwork.title);

  async function confirmApply() {
    if (!hints) return;

    const payload: Partial<Artwork> = {};
    if (fields.title && hints.title) payload.title = hints.title;
    if (fields.artist && hints.artist) payload.artist = hints.artist;
    if (fields.period && hints.period) payload.year_period = hints.period;

    if (!Object.keys(payload).length) return;

    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await api.put<Artwork>(`/api/artworks/${artwork.id}`, payload);
      onApplied(updated);
      setSuccess("Artwork metadata updated.");
      setPendingPreset(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update artwork.");
    } finally {
      setSaving(false);
    }
  }

  const reviewing = pendingPreset !== null;

  return (
    <div className="space-y-3 rounded-xl border border-border bg-muted/20 p-3">
      <div>
        <h4 className="text-sm font-medium">Suggested identification</h4>
        {hints.confidence != null ? (
          <p className="text-xs text-muted-foreground">
            AI confidence: {Math.round(hints.confidence * 100)}%
          </p>
        ) : null}
      </div>

      {showTitleSuggestion && hints.title ? (
        <div className="rounded-lg border border-primary/20 bg-primary/5 px-3 py-2">
          <p className="text-xs text-muted-foreground">
            AI suggested title:{" "}
            <span className="font-medium text-foreground">{hints.title}</span>
          </p>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            className="mt-2 min-h-9"
            disabled={saving || reviewing}
            onClick={() => startReview("title")}
          >
            Use this title
          </Button>
        </div>
      ) : null}

      {!reviewing ? (
        <div className="flex flex-wrap gap-2">
          {hints.title ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="min-h-9"
              disabled={saving}
              onClick={() => startReview("title")}
            >
              Use title
            </Button>
          ) : null}
          {hints.artist ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="min-h-9"
              disabled={saving}
              onClick={() => startReview("artist")}
            >
              Use artist
            </Button>
          ) : null}
          {hints.title && hints.artist ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="min-h-9"
              disabled={saving}
              onClick={() => startReview("both")}
            >
              Use title + artist
            </Button>
          ) : null}
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="min-h-9"
            disabled={saving}
            data-testid="research-review-metadata"
            onClick={() => startReview("review")}
          >
            Review metadata
          </Button>
        </div>
      ) : (
        <div className="space-y-3 rounded-lg border border-border bg-card p-3">
          <p className="text-sm font-medium">Review before saving</p>
          <dl className="space-y-2 text-xs">
            {hints.title ? (
              <div className="grid gap-1 sm:grid-cols-[6rem_1fr]">
                <dt className="text-muted-foreground">Title</dt>
                <dd>
                  <span className="text-muted-foreground line-through">
                    {artwork.title || "Unknown"}
                  </span>
                  {" → "}
                  <span className="font-medium">{hints.title}</span>
                </dd>
              </div>
            ) : null}
            {hints.artist ? (
              <div className="grid gap-1 sm:grid-cols-[6rem_1fr]">
                <dt className="text-muted-foreground">Artist</dt>
                <dd>
                  <span className="text-muted-foreground line-through">
                    {artwork.artist || "Unknown"}
                  </span>
                  {" → "}
                  <span className="font-medium">{hints.artist}</span>
                </dd>
              </div>
            ) : null}
            {hints.period ? (
              <div className="grid gap-1 sm:grid-cols-[6rem_1fr]">
                <dt className="text-muted-foreground">Period</dt>
                <dd>
                  <span className="text-muted-foreground line-through">
                    {artwork.year_period || "—"}
                  </span>
                  {" → "}
                  <span className="font-medium">{hints.period}</span>
                </dd>
              </div>
            ) : null}
          </dl>

          <div className="flex flex-wrap gap-2">
            {hints.title ? (
              <label
                className={cn(
                  "inline-flex min-h-9 cursor-pointer items-center gap-2 rounded-lg border px-2.5 text-xs",
                  fields.title ? "border-primary bg-primary/5" : "border-border"
                )}
              >
                <input
                  type="checkbox"
                  className="size-3.5 accent-primary"
                  checked={fields.title}
                  disabled={saving}
                  onChange={() => setFields((current) => ({ ...current, title: !current.title }))}
                />
                Title
              </label>
            ) : null}
            {hints.artist ? (
              <label
                className={cn(
                  "inline-flex min-h-9 cursor-pointer items-center gap-2 rounded-lg border px-2.5 text-xs",
                  fields.artist ? "border-primary bg-primary/5" : "border-border"
                )}
              >
                <input
                  type="checkbox"
                  className="size-3.5 accent-primary"
                  checked={fields.artist}
                  disabled={saving}
                  onChange={() => setFields((current) => ({ ...current, artist: !current.artist }))}
                />
                Artist
              </label>
            ) : null}
            {hints.period ? (
              <label
                className={cn(
                  "inline-flex min-h-9 cursor-pointer items-center gap-2 rounded-lg border px-2.5 text-xs",
                  fields.period ? "border-primary bg-primary/5" : "border-border"
                )}
              >
                <input
                  type="checkbox"
                  className="size-3.5 accent-primary"
                  checked={fields.period}
                  disabled={saving}
                  onChange={() => setFields((current) => ({ ...current, period: !current.period }))}
                />
                Period
              </label>
            ) : null}
          </div>

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
              disabled={saving || !Object.values(fields).some(Boolean)}
              onClick={() => void confirmApply()}
            >
              {saving ? "Saving…" : "Apply selected"}
            </Button>
          </div>
        </div>
      )}

      {error ? <p className="text-xs text-destructive">{error}</p> : null}
      {success ? <p className="text-xs text-primary">{success}</p> : null}
    </div>
  );
}
