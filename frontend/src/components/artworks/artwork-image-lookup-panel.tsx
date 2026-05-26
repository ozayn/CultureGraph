"use client";

import { useState } from "react";
import { ImageIcon, Loader2 } from "lucide-react";

import { EntryThumbnail } from "@/components/ui/entry-thumbnail";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { Artwork, ArtworkLookupCandidate, ArtworkLookupResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ArtworkImageLookupPanelProps {
  artwork: Artwork;
  museumName: string | null;
  canEdit: boolean;
  onApplied: (artwork: Artwork) => void;
  /** find = primary action when no photo; replace = subtle action when photo exists */
  variant?: "find" | "replace";
  className?: string;
}

function candidateKey(candidate: ArtworkLookupCandidate): string {
  return candidate.external_id ?? candidate.object_url ?? candidate.title;
}

function LookupCandidateCard({
  candidate,
  applying,
  onApply,
}: {
  candidate: ArtworkLookupCandidate;
  applying: boolean;
  onApply: () => void;
}) {
  return (
    <li className="rounded-xl border border-border bg-card p-3">
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
          {candidate.medium ? (
            <p className="text-[11px] text-muted-foreground">{candidate.medium}</p>
          ) : null}
          {candidate.rights_label ? (
            <p className="text-[11px] leading-snug text-muted-foreground">
              {candidate.rights_label}
            </p>
          ) : null}
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button
          type="button"
          size="touch"
          className="flex-1 sm:flex-none"
          disabled={!candidate.image_url || applying}
          onClick={onApply}
        >
          {applying ? "Saving…" : "Use this image"}
        </Button>
        {candidate.object_url ? (
          <a
            href={candidate.object_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-h-11 items-center px-2 text-sm text-muted-foreground underline-offset-2 hover:underline"
          >
            View record
          </a>
        ) : null}
      </div>
    </li>
  );
}

export function ArtworkImageLookupPanel({
  artwork,
  museumName,
  canEdit,
  onApplied,
  variant = "find",
  className,
}: ArtworkImageLookupPanelProps) {
  const [sheetOpen, setSheetOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [applyingId, setApplyingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ArtworkLookupResponse | null>(null);

  const ngaVisit = museumName ? museumName.toLowerCase().includes("national gallery of art") : false;

  async function runLookup() {
    setLoading(true);
    setError(null);
    setResponse(null);
    try {
      const params = new URLSearchParams({ source: "nga" });
      const result = await api.get<ArtworkLookupResponse>(
        `/api/artworks/${artwork.id}/lookup-image?${params.toString()}`
      );
      setResponse(result);

      if (!result.candidates.length) {
        if (result.notice) {
          setError(result.notice);
        } else if (!artwork.title?.trim() && !artwork.artist?.trim()) {
          setError("Add a title or artist on this artwork to improve matching.");
        } else if (!ngaVisit) {
          setError(
            "No matches in the National Gallery open collection. This artwork is not linked to an NGA visit — results may be less accurate."
          );
        } else {
          setError("No close matches found in the National Gallery open collection index.");
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lookup failed. Check your connection and try again.");
      setResponse(null);
    } finally {
      setLoading(false);
    }
  }

  async function openLookup() {
    setSheetOpen(true);
    await runLookup();
  }

  async function applyCandidate(candidate: ArtworkLookupCandidate) {
    const key = candidateKey(candidate);
    setApplyingId(key);
    setError(null);
    try {
      const updated = await api.put<Artwork>(`/api/artworks/${artwork.id}`, {
        image_url: candidate.image_url,
        image_thumbnail_url: candidate.image_thumbnail_url ?? candidate.image_url,
        catalog_source: candidate.source_name,
        catalog_object_url: candidate.object_url,
        catalog_accession_number: candidate.accession_number,
        catalog_rights_label: candidate.rights_label,
        medium: artwork.medium ?? candidate.medium,
        year_period: artwork.year_period ?? candidate.date,
      });
      onApplied(updated);
      setSheetOpen(false);
      setResponse(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save image.");
    } finally {
      setApplyingId(null);
    }
  }

  if (!canEdit) {
    return null;
  }

  const trigger =
    variant === "replace" ? (
      <Button
        type="button"
        variant="ghost"
        size="touch"
        className={cn("h-auto min-h-11 px-2 text-sm text-muted-foreground", className)}
        onClick={() => void openLookup()}
      >
        Replace image
      </Button>
    ) : (
      <Button
        type="button"
        variant="outline"
        size="touch"
        className={cn("gap-2 text-muted-foreground", className)}
        onClick={() => void openLookup()}
      >
        <ImageIcon className="size-4" strokeWidth={1.75} />
        Find official image
      </Button>
    );

  return (
    <>
      {trigger}

      <BottomSheet
        open={sheetOpen}
        onOpenChange={(open) => {
          setSheetOpen(open);
          if (!open) {
            setError(null);
            setResponse(null);
          }
        }}
        title="Find official image"
        description="Suggested matches from open museum collection records. Review before applying."
        footer={
          response?.candidates.length ? (
            <p className="text-center text-xs text-muted-foreground">
              {response.candidates.length} candidate{response.candidates.length === 1 ? "" : "s"} ·
              tap Use this image to apply
            </p>
          ) : null
        }
      >
        <div className="space-y-4">
          <div className="rounded-lg border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
            Searching: National Gallery of Art open collection
            {!ngaVisit ? " (title/artist match; visit museum not NGA)" : null}
          </div>

          {loading ? (
            <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Searching collection…
            </div>
          ) : null}

          {error ? <p className="text-sm text-destructive">{error}</p> : null}

          {response?.disclaimer ? (
            <p className="text-xs leading-relaxed text-muted-foreground">{response.disclaimer}</p>
          ) : null}

          {!loading && response?.candidates.length ? (
            <ul className="space-y-3">
              {response.candidates.map((candidate) => {
                const key = candidateKey(candidate);
                return (
                  <LookupCandidateCard
                    key={key}
                    candidate={candidate}
                    applying={applyingId === key}
                    onApply={() => void applyCandidate(candidate)}
                  />
                );
              })}
            </ul>
          ) : null}

          {!loading && response && !response.candidates.length && !error ? (
            <p className="py-4 text-sm text-muted-foreground">
              No matches found. Try editing the title or artist, then search again.
            </p>
          ) : null}

          {!loading ? (
            <Button
              type="button"
              variant="outline"
              size="touch"
              className="w-full"
              onClick={() => void runLookup()}
            >
              Search again
            </Button>
          ) : null}
        </div>
      </BottomSheet>
    </>
  );
}
