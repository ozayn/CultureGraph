"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { ImageIcon, Loader2 } from "lucide-react";

import { EntryThumbnail } from "@/components/ui/entry-thumbnail";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { Artwork, ArtworkLookupCandidate, ArtworkLookupResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ArtworkImageLookupContextValue {
  openLookup: () => void;
  canEdit: boolean;
  hasImage: boolean;
}

const ArtworkImageLookupContext = createContext<ArtworkImageLookupContextValue | null>(null);

interface ArtworkImageLookupProviderProps {
  artwork: Artwork;
  canEdit: boolean;
  hasImage: boolean;
  onApplied: (artwork: Artwork) => void;
  children: ReactNode;
}

function candidateKey(candidate: ArtworkLookupCandidate): string {
  return candidate.external_id ?? candidate.object_url ?? candidate.title;
}

function lookupEndpoint(artworkId: number): string {
  return `/api/artworks/${artworkId}/lookup-image?source=all`;
}

function sourcesBannerLabel(sources: string[] | undefined): string {
  if (!sources?.length) {
    return "National Gallery of Art and Smithsonian Open Access";
  }
  return sources.join(" · ");
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

export function ArtworkImageLookupProvider({
  artwork,
  canEdit,
  hasImage,
  onApplied,
  children,
}: ArtworkImageLookupProviderProps) {
  const [sheetOpen, setSheetOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [applyingId, setApplyingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ArtworkLookupResponse | null>(null);

  const runLookup = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResponse(null);
    try {
      const result = await api.get<ArtworkLookupResponse>(lookupEndpoint(artwork.id));
      setResponse(result);

      if (!result.candidates.length) {
        if (result.notice) {
          setError(result.notice);
        } else if (!artwork.title?.trim() && !artwork.artist?.trim()) {
          setError("Add a title or artist on this artwork to improve matching.");
        } else {
          setError("No close matches found in the open collection indexes.");
        }
      }
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Lookup failed. Check your connection and try again."
      );
      setResponse(null);
    } finally {
      setLoading(false);
    }
  }, [artwork.artist, artwork.id, artwork.title]);

  const openLookup = useCallback(() => {
    if (!canEdit) return;
    setSheetOpen(true);
    void runLookup();
  }, [canEdit, runLookup]);

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

  const contextValue = useMemo(
    () => ({ openLookup, canEdit, hasImage }),
    [canEdit, hasImage, openLookup]
  );

  return (
    <ArtworkImageLookupContext.Provider value={contextValue}>
      {children}

      <BottomSheet
        open={sheetOpen}
        onOpenChange={(open) => {
          setSheetOpen(open);
          if (!open) {
            setError(null);
            setResponse(null);
          }
        }}
        title={hasImage ? "Replace official image" : "Find official image"}
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
            Searching: {sourcesBannerLabel(response?.sources_searched)}
          </div>

          {loading ? (
            <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Searching collections…
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
    </ArtworkImageLookupContext.Provider>
  );
}

function useArtworkImageLookup(): ArtworkImageLookupContextValue {
  const context = useContext(ArtworkImageLookupContext);
  if (!context) {
    throw new Error("ArtworkImageLookupTrigger must be used within ArtworkImageLookupProvider.");
  }
  return context;
}

export { useArtworkImageLookup };

interface ArtworkImageLookupTriggerProps {
  variant?: "find" | "replace";
  className?: string;
}

export function ArtworkImageLookupTrigger({
  variant = "find",
  className,
}: ArtworkImageLookupTriggerProps) {
  const { openLookup, canEdit, hasImage } = useArtworkImageLookup();

  if (!canEdit) {
    return null;
  }

  const resolvedVariant = variant === "replace" || hasImage ? "replace" : "find";

  if (resolvedVariant === "replace") {
    return (
      <Button
        type="button"
        variant="outline"
        size="touch"
        className={cn("gap-2", className)}
        onClick={openLookup}
      >
        Replace image
      </Button>
    );
  }

  return (
    <Button
      type="button"
      variant="outline"
      size="touch"
      className={cn("gap-2", className)}
      onClick={openLookup}
    >
      <ImageIcon className="size-4" strokeWidth={1.75} />
      Find official image
    </Button>
  );
}

/** @deprecated Use ArtworkImageLookupProvider + ArtworkImageLookupTrigger */
export function ArtworkImageLookupPanel({
  artwork,
  canEdit,
  onApplied,
  variant = "find",
  className,
}: {
  artwork: Artwork;
  museumName?: string | null;
  canEdit: boolean;
  onApplied: (artwork: Artwork) => void;
  variant?: "find" | "replace";
  className?: string;
}) {
  const hasImage = Boolean(artwork.image_url);
  return (
    <ArtworkImageLookupProvider
      artwork={artwork}
      canEdit={canEdit}
      hasImage={hasImage}
      onApplied={onApplied}
    >
      <ArtworkImageLookupTrigger variant={variant} className={className} />
    </ArtworkImageLookupProvider>
  );
}

export function ArtworkImageLookupSignInHint({ className }: { className?: string }) {
  return (
    <p className={cn("text-xs text-muted-foreground", className)}>
      Sign in to find or replace official museum images.
    </p>
  );
}

export function ArtworkImageLookupDebug({
  canEdit,
  hasImage,
  imageUrl,
  lookupMounted,
}: {
  canEdit: boolean;
  hasImage: boolean;
  imageUrl: string | null;
  lookupMounted: boolean;
}) {
  if (process.env.NODE_ENV !== "development") {
    return null;
  }

  return (
    <p className="rounded border border-amber-300/60 bg-amber-50 px-2 py-1 font-mono text-[10px] text-amber-950">
      lookup debug · isAdmin={String(canEdit)} · hasImage={String(hasImage)} · image_url=
      {imageUrl ?? "null"} · panel={lookupMounted ? "mounted" : "no"}
    </p>
  );
}
