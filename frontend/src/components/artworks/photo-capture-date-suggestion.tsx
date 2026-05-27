"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { formatCalendarDate, isoToCalendarDate } from "@/lib/calendar-date";
import type { Artwork, Visit } from "@/lib/types";

interface PhotoCaptureDateSuggestionProps {
  artwork: Artwork;
  onDismiss?: () => void;
  onVisitUpdated?: (visit: Visit) => void;
  className?: string;
}

function formatCaptureDate(iso: string): string {
  const calendar = isoToCalendarDate(iso);
  if (calendar) return formatCalendarDate(calendar);
  return iso;
}

function captureDateOnly(iso: string): string {
  return isoToCalendarDate(iso) ?? iso.slice(0, 10);
}

export function PhotoCaptureDateSuggestion({
  artwork,
  onDismiss,
  onVisitUpdated,
  className,
}: PhotoCaptureDateSuggestionProps) {
  const [visible, setVisible] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [applied, setApplied] = useState(false);

  if (
    !visible ||
    applied ||
    artwork.captured_date_source !== "exif" ||
    !artwork.captured_at
  ) {
    return null;
  }

  const formattedDate = formatCaptureDate(artwork.captured_at);
  const hasVisit = artwork.visit_id != null;

  function dismiss() {
    setVisible(false);
    onDismiss?.();
  }

  async function applyPhotoDate() {
    if (!artwork.captured_at || !artwork.visit_id) return;

    setLoading(true);
    setError(null);
    try {
      const updatedVisit = await api.patch<Visit>(`/api/visits/${artwork.visit_id}`, {
        visit_date: captureDateOnly(artwork.captured_at),
      });
      setApplied(true);
      setVisible(false);
      onVisitUpdated?.(updatedVisit);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update visit date.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className={`rounded-xl border border-border bg-muted/30 px-4 py-3 text-sm ${className ?? ""}`}
    >
      <p className="leading-relaxed text-foreground">
        This photo appears to have been taken on{" "}
        <span className="font-medium">{formattedDate}</span>.
        {hasVisit ? " Use this date for the visit?" : null}
      </p>

      {hasVisit ? (
        <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center">
          <Button
            type="button"
            size="sm"
            disabled={loading}
            onClick={() => void applyPhotoDate()}
          >
            {loading ? "Updating…" : "Use photo date"}
          </Button>
          <button
            type="button"
            className="min-h-9 px-1 text-sm text-muted-foreground underline-offset-2 hover:underline"
            onClick={dismiss}
          >
            Not now
          </button>
        </div>
      ) : (
        <button
          type="button"
          className="mt-2 min-h-9 text-sm text-muted-foreground underline-offset-2 hover:underline"
          onClick={dismiss}
        >
          Dismiss
        </button>
      )}

      {error ? <p className="mt-2 text-sm text-destructive">{error}</p> : null}
    </div>
  );
}
