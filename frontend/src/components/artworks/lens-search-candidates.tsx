"use client";

import { ExternalLink } from "lucide-react";
import { useState } from "react";

import { EntryThumbnail } from "@/components/ui/entry-thumbnail";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { Artwork, LensSearchCandidate, LensSearchResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

const WEB_VISUAL_SEARCH_SOURCE = "Web visual search";

function candidateKey(candidate: LensSearchCandidate): string {
  return candidate.source_url ?? candidate.image_url ?? candidate.title;
}

function confidenceLabel(candidate: LensSearchCandidate): string {
  if (candidate.confidence_label === "high") {
    return "Strong web match";
  }
  if (candidate.confidence_label === "possible") {
    return "Possible web match";
  }
  return "Related web result";
}

interface LensSearchCandidateListProps {
  artwork: Artwork;
  search: LensSearchResponse;
  canEdit?: boolean;
  onApplied: (artwork: Artwork) => void;
}

export function LensSearchCandidateList({
  artwork,
  search,
  canEdit = true,
  onApplied,
}: LensSearchCandidateListProps) {
  const [applying, setApplying] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function applyCandidate(
    candidate: LensSearchCandidate,
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
        payload.catalog_source = search.provider ?? WEB_VISUAL_SEARCH_SOURCE;
        payload.catalog_object_url = candidate.source_url ?? undefined;
      }

      if (mode === "image_metadata" && candidate.title) {
        payload.title = candidate.title;
      }

      const updated = await api.put<Artwork>(`/api/artworks/${artwork.id}`, payload);
      onApplied(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not apply web visual match.");
    } finally {
      setApplying(null);
    }
  }

  if (!search.candidates.length) {
    return search.notice ? (
      <p className="text-sm text-muted-foreground">{search.notice}</p>
    ) : null;
  }

  return (
    <div className="space-y-4 rounded-xl border border-dashed border-border bg-muted/10 p-4">
      <div>
        <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
          {search.provider ?? WEB_VISUAL_SEARCH_SOURCE}
        </p>
        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
          {search.disclaimer ??
            "Third-party web results. Review each source before applying any image or metadata."}
        </p>
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <ul className="space-y-3">
        {search.candidates.slice(0, 6).map((candidate) => {
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
                    {candidate.source} · rank {candidate.source_rank}
                  </p>
                  {candidate.snippet ? (
                    <p className="text-[11px] text-muted-foreground">{candidate.snippet}</p>
                  ) : null}
                  <p className="text-[11px] font-medium text-primary">
                    {confidenceLabel(candidate)}
                  </p>
                </div>
              </div>

              <div className="mt-3 flex flex-col gap-2">
                {candidate.source_url ? (
                  <a
                    href={candidate.source_url}
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
                        : "Use image + title"}
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
