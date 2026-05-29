"use client";

import { ExternalLink } from "lucide-react";
import { useState } from "react";

import { EntryThumbnail } from "@/components/ui/entry-thumbnail";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { museumShortLabel } from "@/lib/museum-collection";
import type { Artwork, VisualMatchCandidate, VisualMatchResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

function candidateKey(candidate: VisualMatchCandidate): string {
  return candidate.external_id ?? candidate.object_url ?? candidate.title;
}

function confidenceLabel(candidate: VisualMatchCandidate): string {
  if (candidate.confidence_label === "high") {
    return "Strong visual match";
  }
  if (candidate.confidence_label === "possible") {
    return "Best visual match";
  }
  return "Related visual match";
}

interface VisualMatchCandidateListProps {
  artwork: Artwork;
  match: VisualMatchResponse;
  canEdit?: boolean;
  onApplied: (artwork: Artwork) => void;
}

function visualIndexNotice(match: VisualMatchResponse): string | null {
  if (match.index_status === "empty") {
    return "NGA visual index is still building.";
  }
  if (match.indexed_count && match.indexed_count > 0) {
    return `NGA visual index: ${match.indexed_count.toLocaleString()} artworks indexed.`;
  }
  return match.notice ?? null;
}

export function VisualMatchCandidateList({
  artwork,
  match,
  canEdit = true,
  onApplied,
}: VisualMatchCandidateListProps) {
  const [applying, setApplying] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const shortLabel = museumShortLabel(match.museum_collection_name);
  const heading = shortLabel
    ? `Best visual matches in ${shortLabel}`
    : "Best visual matches";

  async function applyCandidate(
    candidate: VisualMatchCandidate,
    mode: "image" | "image_metadata"
  ) {
    setApplying(`${candidateKey(candidate)}:${mode}`);
    setError(null);
    try {
      const payload: Partial<Artwork> = {};
      if (candidate.image_url) {
        payload.image_url = candidate.image_url;
        payload.image_thumbnail_url = candidate.thumbnail_url ?? candidate.image_url;
        payload.catalog_image_url = candidate.image_url;
        payload.catalog_thumbnail_url = candidate.thumbnail_url ?? candidate.image_url;
        payload.catalog_source = candidate.source_name;
        payload.catalog_accession_number = candidate.accession_number ?? undefined;
        payload.catalog_rights_label = candidate.rights_label ?? undefined;
        payload.catalog_object_url = candidate.object_url ?? undefined;
      }

      if (mode === "image_metadata") {
        if (candidate.title) payload.title = candidate.title;
        if (candidate.artist) payload.artist = candidate.artist;
        if (candidate.date) payload.year_period = candidate.date;
        if (candidate.medium) payload.medium = candidate.medium;
      }

      const updated = await api.put<Artwork>(`/api/artworks/${artwork.id}`, payload);
      onApplied(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not apply visual match.");
    } finally {
      setApplying(null);
    }
  }

  if (!match.candidates.length) {
    const notice = visualIndexNotice(match);
    return notice ? (
      <p className="text-sm text-muted-foreground">{notice}</p>
    ) : null;
  }

  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">{heading}</p>
        {match.indexed_count && match.indexed_count > 0 ? (
          <p className="mt-1 text-[11px] text-muted-foreground">
            Searching {match.indexed_count.toLocaleString()} indexed NGA artworks
          </p>
        ) : null}
        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
          {match.disclaimer ??
            "Compare catalog thumbnails with your photo before applying metadata."}
        </p>
        {match.museum_collection_name ? (
          <p className="mt-1 text-[11px] text-muted-foreground">
            Searching {match.museum_collection_name} by visual similarity
          </p>
        ) : null}
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <ul className="space-y-3">
        {match.candidates.slice(0, 6).map((candidate) => {
          const key = candidateKey(candidate);
          const busy = applying?.startsWith(key) ?? false;
          const busyMode = applying?.split(":")[1];
          const weak = candidate.confidence_label === "weak";

          return (
            <li
              key={key}
              className={cn(
                "rounded-xl border border-border bg-card p-3",
                weak && "opacity-90"
              )}
            >
              <div className="flex gap-3">
                <EntryThumbnail
                  imageUrl={candidate.thumbnail_url ?? candidate.image_url}
                  alt={candidate.title}
                  entityType="artwork"
                  size="lg"
                />
                <div className="min-w-0 flex-1 space-y-1">
                  <p className="text-sm font-medium leading-snug">{candidate.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {[candidate.artist, candidate.date, candidate.medium]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {candidate.source_name} · visual {Math.round(candidate.similarity_score * 100)}%
                  </p>
                  <p className="text-[11px] text-muted-foreground">{candidate.match_reason}</p>
                  <p className="text-[11px] font-medium text-primary">
                    {confidenceLabel(candidate)}
                  </p>
                </div>
              </div>

              <div className="mt-3 flex flex-col gap-2">
                {candidate.object_url ? (
                  <a
                    href={candidate.object_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                  >
                    View source
                    <ExternalLink className="size-3" aria-hidden />
                  </a>
                ) : null}

                {canEdit ? (
                  <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                    <Button
                      type="button"
                      size="sm"
                      disabled={!candidate.image_url || busy}
                      onClick={() => void applyCandidate(candidate, "image")}
                    >
                      {busy && busyMode === "image" ? "Applying…" : "Use image"}
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      disabled={!candidate.image_url || busy}
                      onClick={() => void applyCandidate(candidate, "image_metadata")}
                    >
                      {busy && busyMode === "image_metadata"
                        ? "Applying…"
                        : "Use image + metadata"}
                    </Button>
                  </div>
                ) : null}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
