"use client";

import { useState } from "react";
import { ImageIcon, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { Artwork, ArtworkLookupCandidate, ArtworkLookupResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ArtworkImageLookupPanelProps {
  artwork: Artwork;
  museumName: string | null;
  canEdit: boolean;
  onApplied: (artwork: Artwork) => void;
}

export function ArtworkImageLookupPanel({
  artwork,
  museumName,
  canEdit,
  onApplied,
}: ArtworkImageLookupPanelProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [applyingId, setApplyingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ArtworkLookupResponse | null>(null);

  const ngaMuseum = museumName ? museumName.toLowerCase().includes("national gallery of art") : false;

  async function runLookup() {
    setOpen(true);
    setLoading(true);
    setError(null);
    try {
      const result = await api.get<ArtworkLookupResponse>(
        `/api/artworks/${artwork.id}/lookup-image`
      );
      setResponse(result);
      if (!result.candidates.length) {
        setError(
          ngaMuseum
            ? "No close matches found in the National Gallery open collection index."
            : "No lookup source matched this museum. Try linking the visit to National Gallery of Art."
        );
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lookup failed.");
      setResponse(null);
    } finally {
      setLoading(false);
    }
  }

  async function applyCandidate(candidate: ArtworkLookupCandidate) {
    const key = candidate.external_id ?? candidate.object_url ?? candidate.title;
    setApplyingId(key);
    setError(null);
    try {
      const updated = await api.put<Artwork>(`/api/artworks/${artwork.id}`, {
        image_url: candidate.image_url,
        catalog_source: candidate.source_name,
        catalog_object_url: candidate.object_url,
        catalog_accession_number: candidate.accession_number,
        catalog_rights_label: candidate.rights_label,
        medium: artwork.medium ?? candidate.medium,
        year_period: artwork.year_period ?? candidate.date,
      });
      onApplied(updated);
      setOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save image.");
    } finally {
      setApplyingId(null);
    }
  }

  if (!canEdit) {
    return null;
  }

  if (!ngaMuseum) {
    return (
      <p className="px-4 text-xs leading-relaxed text-muted-foreground sm:px-0">
        Official image lookup is available for National Gallery of Art visits.
      </p>
    );
  }

  return (
    <section className="px-4 sm:px-0">
      {!open ? (
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="min-h-11 gap-2 text-muted-foreground"
          onClick={() => void runLookup()}
        >
          <ImageIcon className="size-4" strokeWidth={1.75} />
          Find official image
        </Button>
      ) : (
        <div className="space-y-3 rounded-xl border border-border bg-card p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                Collection lookup
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                Suggested matches from open museum records. Review before applying.
              </p>
            </div>
            <button
              type="button"
              className="text-sm text-muted-foreground underline-offset-2 hover:underline"
              onClick={() => setOpen(false)}
            >
              Close
            </button>
          </div>

          {loading ? (
            <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Searching collection…
            </div>
          ) : null}

          {error ? <p className="text-sm text-destructive">{error}</p> : null}

          {response?.disclaimer ? (
            <p className="text-xs leading-relaxed text-muted-foreground">{response.disclaimer}</p>
          ) : null}

          {response?.candidates.length ? (
            <ul className="space-y-3">
              {response.candidates.map((candidate) => {
                const key =
                  candidate.external_id ?? candidate.object_url ?? candidate.title;
                return (
                  <li
                    key={key}
                    className="flex gap-3 rounded-lg border border-border p-3"
                  >
                    {candidate.image_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={candidate.image_url}
                        alt=""
                        className="size-16 shrink-0 rounded-md object-cover ring-1 ring-border"
                      />
                    ) : (
                      <div className="flex size-16 shrink-0 items-center justify-center rounded-md bg-muted text-xs text-muted-foreground">
                        No image
                      </div>
                    )}
                    <div className="min-w-0 flex-1 space-y-1">
                      <p className="truncate text-sm font-medium">{candidate.title}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {[candidate.artist, candidate.date].filter(Boolean).join(" · ")}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {candidate.source_name}
                        {candidate.confidence != null
                          ? ` · ${Math.round(candidate.confidence * 100)}% match`
                          : null}
                      </p>
                      {candidate.rights_label ? (
                        <p className="text-[11px] leading-snug text-muted-foreground">
                          {candidate.rights_label}
                        </p>
                      ) : null}
                      <div className="flex flex-wrap gap-2 pt-1">
                        <Button
                          type="button"
                          size="sm"
                          className="min-h-9"
                          disabled={!candidate.image_url || applyingId === key}
                          onClick={() => void applyCandidate(candidate)}
                        >
                          {applyingId === key ? "Saving…" : "Use this image"}
                        </Button>
                        {candidate.object_url ? (
                          <a
                            href={candidate.object_url}
                            target="_blank"
                            rel="noreferrer"
                            className={cn(
                              "inline-flex min-h-9 items-center text-xs text-muted-foreground underline-offset-2 hover:underline"
                            )}
                          >
                            View record
                          </a>
                        ) : null}
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : null}
        </div>
      )}
    </section>
  );
}
