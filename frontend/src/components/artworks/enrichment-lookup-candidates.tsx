"use client";

import { ExternalLink } from "lucide-react";
import { useState } from "react";

import { EntryThumbnail } from "@/components/ui/entry-thumbnail";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { HIGH_CONFIDENCE_THRESHOLD } from "@/lib/artwork-metadata";
import type {
  Artwork,
  ArtworkIdentification,
  ArtworkLookupCandidate,
  ArtworkLookupResponse,
} from "@/lib/types";
import { cn } from "@/lib/utils";

function candidateKey(candidate: ArtworkLookupCandidate): string {
  return candidate.external_id ?? candidate.object_url ?? candidate.title;
}

interface LookupCandidateListProps {
  artwork: Artwork;
  lookup: ArtworkLookupResponse;
  identification?: ArtworkIdentification | null;
  canEdit?: boolean;
  onApplied: (artwork: Artwork) => void;
}

function sectionHeading(identification?: ArtworkIdentification | null): string {
  if (identification?.identification_mode === "style_subject") {
    return "Related official records";
  }
  return "Possible official records";
}

function sectionDescription(
  lookup: ArtworkLookupResponse,
  identification?: ArtworkIdentification | null
): string | null {
  if (lookup.notice) return lookup.notice;
  if (identification?.identification_mode === "catalog_match") {
    return "Review the source page and image before applying metadata.";
  }
  if (identification?.identification_mode === "possible_match") {
    return "These are related collection records — verify against your photo before applying.";
  }
  if (identification?.identification_mode === "style_subject") {
    return "No exact catalog match yet. Compare these related records with your photo.";
  }
  return lookup.query_used
    ? `Searched open collections for “${lookup.query_used}”.`
    : null;
}

export function LookupCandidateList({
  artwork,
  lookup,
  identification = null,
  canEdit = true,
  onApplied,
}: LookupCandidateListProps) {
  const [applying, setApplying] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function applyCandidate(
    candidate: ArtworkLookupCandidate,
    mode: "image" | "image_metadata"
  ) {
    setApplying(`${candidateKey(candidate)}:${mode}`);
    setError(null);
    try {
      const payload: Partial<Artwork> = {};
      if (candidate.image_url) {
        payload.image_url = candidate.image_url;
        payload.image_thumbnail_url = candidate.image_thumbnail_url ?? candidate.image_url;
        payload.catalog_image_url = candidate.image_url;
        payload.catalog_thumbnail_url = candidate.image_thumbnail_url ?? candidate.image_url;
        payload.catalog_source = candidate.source_name;
        payload.catalog_accession_number = candidate.accession_number;
        payload.catalog_rights_label = candidate.rights_label;
        payload.catalog_object_url = candidate.object_url;
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

  const description = sectionDescription(lookup, identification);
  const likelyMatches = lookup.candidates.filter((candidate) => !candidate.low_confidence);
  const relatedMatches = lookup.candidates.filter((candidate) => candidate.low_confidence);
  const displayLikely = likelyMatches.length > 0 ? likelyMatches : lookup.candidates.slice(0, 3);
  const displayRelated =
    likelyMatches.length > 0 ? relatedMatches : lookup.candidates.slice(3, 6);

  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
          {sectionHeading(identification)}
        </p>
        {description ? (
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{description}</p>
        ) : null}
        {lookup.sources_searched.length > 0 ? (
          <p className="mt-1 text-[11px] text-muted-foreground">
            Sources: {lookup.sources_searched.join(" · ")}
          </p>
        ) : null}
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <CandidateGroup
        title={displayRelated.length > 0 && displayLikely.length > 0 ? "Best matches" : undefined}
        candidates={displayLikely.slice(0, 4)}
        artwork={artwork}
        canEdit={canEdit}
        applying={applying}
        onApply={applyCandidate}
      />

      {displayRelated.length > 0 ? (
        <CandidateGroup
          title="Related records"
          candidates={displayRelated.slice(0, 3)}
          artwork={artwork}
          canEdit={canEdit}
          applying={applying}
          onApply={applyCandidate}
          subdued
        />
      ) : null}
    </div>
  );
}

function CandidateGroup({
  title,
  candidates,
  artwork,
  canEdit,
  applying,
  onApply,
  subdued = false,
}: {
  title?: string;
  candidates: ArtworkLookupCandidate[];
  artwork: Artwork;
  canEdit: boolean;
  applying: string | null;
  onApply: (candidate: ArtworkLookupCandidate, mode: "image" | "image_metadata") => void;
  subdued?: boolean;
}) {
  if (!candidates.length) return null;

  return (
    <div className="space-y-2">
      {title ? <p className="text-xs font-medium text-muted-foreground">{title}</p> : null}
      <ul className="space-y-3">
        {candidates.map((candidate) => {
          const key = candidateKey(candidate);
          const busy = applying?.startsWith(key) ?? false;
          const busyMode = applying?.split(":")[1];
          const highConfidence =
            !candidate.low_confidence &&
            (candidate.confidence ?? 0) >= HIGH_CONFIDENCE_THRESHOLD;

          return (
            <li
              key={key}
              className={cn(
                "rounded-xl border border-border bg-card p-3",
                (subdued || candidate.low_confidence) && "opacity-85"
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
                    {[candidate.artist, candidate.date, candidate.medium]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {candidate.source_name}
                    {candidate.confidence != null
                      ? ` · ${Math.round(candidate.confidence * 100)}% match`
                      : null}
                    {candidate.low_confidence ? " · verify carefully" : null}
                  </p>
                  {candidate.match_reasons && candidate.match_reasons.length > 0 ? (
                    <p className="text-[11px] text-muted-foreground">
                      {candidate.match_reasons.slice(0, 2).join(" · ")}
                    </p>
                  ) : null}
                  {highConfidence ? (
                    <p className="text-[11px] font-medium text-primary">Strong catalog similarity</p>
                  ) : null}
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
                      onClick={() => void onApply(candidate, "image")}
                    >
                      {busy && busyMode === "image" ? "Applying…" : "Use image"}
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      disabled={!candidate.image_url || busy}
                      onClick={() => void onApply(candidate, "image_metadata")}
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
