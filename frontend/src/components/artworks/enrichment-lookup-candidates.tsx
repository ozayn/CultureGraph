"use client";

import { useState } from "react";

import { EntryThumbnail } from "@/components/ui/entry-thumbnail";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { isPlaceholderTitle } from "@/lib/artwork-metadata";
import type { Artwork, ArtworkLookupCandidate, ArtworkLookupResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

function candidateKey(candidate: ArtworkLookupCandidate): string {
  return candidate.external_id ?? candidate.object_url ?? candidate.title;
}

interface LookupCandidateListProps {
  artwork: Artwork;
  lookup: ArtworkLookupResponse;
  canEdit?: boolean;
  onApplied: (artwork: Artwork) => void;
}

export function LookupCandidateList({
  artwork,
  lookup,
  canEdit = true,
  onApplied,
}: LookupCandidateListProps) {
  const [applying, setApplying] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function applyCandidate(
    candidate: ArtworkLookupCandidate,
    mode: "image" | "image_title" | "title"
  ) {
    setApplying(candidateKey(candidate));
    setError(null);
    try {
      const payload: Partial<Artwork> = {};
      if ((mode === "image" || mode === "image_title") && candidate.image_url) {
        payload.image_url = candidate.image_url;
        payload.image_thumbnail_url = candidate.image_thumbnail_url ?? candidate.image_url;
        payload.catalog_image_url = candidate.image_url;
        payload.catalog_thumbnail_url = candidate.image_thumbnail_url ?? candidate.image_url;
        payload.catalog_source = candidate.source_name;
        payload.catalog_accession_number = candidate.accession_number;
        payload.catalog_rights_label = candidate.rights_label;
        payload.catalog_object_url = candidate.object_url;
      }
      if ((mode === "image_title" || mode === "title") && candidate.title) {
        payload.title = candidate.title;
      }
      if (candidate.artist) payload.artist = candidate.artist;
      if (candidate.date) payload.year_period = candidate.date;
      if (candidate.medium) payload.medium = candidate.medium;

      const updated = await api.put<Artwork>(`/api/artworks/${artwork.id}`, payload);
      onApplied(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not apply collection match.");
    } finally {
      setApplying(null);
    }
  }

  if (!lookup.candidates.length) {
    return lookup.notice ? (
      <p className="text-sm text-muted-foreground">{lookup.notice}</p>
    ) : null;
  }

  return (
    <div className="space-y-3">
      <div>
        <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
          Official collection matches
        </p>
        {lookup.query_used ? (
          <p className="mt-1 text-xs text-muted-foreground">
            Searched for “{lookup.query_used}”
          </p>
        ) : null}
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <ul className="space-y-3">
        {lookup.candidates.slice(0, 4).map((candidate) => {
          const key = candidateKey(candidate);
          const busy = applying === key;
          const suggestTitle =
            isPlaceholderTitle(artwork.title) &&
            Boolean(candidate.title?.trim()) &&
            !candidate.low_confidence;

          return (
            <li
              key={key}
              className={cn(
                "rounded-xl border border-border bg-card p-3",
                candidate.low_confidence && "opacity-75"
              )}
            >
              <div className="flex gap-3">
                <EntryThumbnail
                  imageUrl={candidate.image_thumbnail_url ?? candidate.image_url}
                  alt={candidate.title}
                  entityType="artwork"
                  size="lg"
                />
                <div className="min-w-0 flex-1 space-y-1">
                  <p className="text-sm font-medium leading-snug">{candidate.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {[candidate.artist, candidate.date].filter(Boolean).join(" · ")}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {candidate.source_name}
                    {candidate.confidence != null
                      ? ` · ${Math.round(candidate.confidence * 100)}% match`
                      : null}
                  </p>
                  {suggestTitle ? (
                    <p className="text-[11px] font-medium text-primary">Suggested title</p>
                  ) : null}
                </div>
              </div>
              {canEdit ? (
                <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                  <Button
                    type="button"
                    size="sm"
                    disabled={!candidate.image_url || busy}
                    onClick={() => void applyCandidate(candidate, "image")}
                  >
                    {busy ? "Applying…" : "Use image"}
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    disabled={!candidate.image_url || !candidate.title?.trim() || busy}
                    onClick={() => void applyCandidate(candidate, "image_title")}
                  >
                    Use image + title
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    disabled={!candidate.title?.trim() || busy}
                    onClick={() => void applyCandidate(candidate, "title")}
                  >
                    Title only
                  </Button>
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
