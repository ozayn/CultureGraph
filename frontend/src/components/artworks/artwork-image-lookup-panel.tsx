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
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { isPlaceholderTitle } from "@/lib/artwork-metadata";
import type {
  Artwork,
  ArtworkLookupCandidate,
  ArtworkLookupQuerySource,
  ArtworkLookupQueryStrategy,
  ArtworkLookupResponse,
} from "@/lib/types";
import { cn } from "@/lib/utils";

const MISSING_METADATA_HINT = "Add a title or artist to improve search results.";

const QUERY_SOURCE_LABELS: Record<ArtworkLookupQuerySource, string> = {
  ai_title: "AI title",
  saved_title: "Saved title",
  artist_notes: "Artist + notes",
  manual: "Manual search",
};

const QUERY_STRATEGY_LABELS: Record<ArtworkLookupQueryStrategy, string> = {
  exact: "Exact title match",
  fuzzy: "Fuzzy title match",
  artist_fallback: "Related works by artist",
  broad: "Broad collection search",
};

interface LookupSearchParams {
  title?: string;
  artist?: string;
  searchMode?: "broad";
}

interface ApplyFields {
  image: boolean;
  title: boolean;
  artist: boolean;
  date: boolean;
  medium: boolean;
  sourceUrl: boolean;
}

interface PendingApply {
  candidate: ArtworkLookupCandidate;
  fields: ApplyFields;
}

interface ArtworkImageLookupContextValue {
  openLookup: () => void;
  canEdit: boolean;
  hasImage: boolean;
}

const ArtworkImageLookupContext = createContext<ArtworkImageLookupContextValue | null>(null);

export interface ArtworkImageLookupPanelProps {
  artwork: Artwork;
  canEdit: boolean;
  hasImage: boolean;
  aiTitleHint?: string | null;
  aiArtistHint?: string | null;
  onApplied: (artwork: Artwork) => void;
  children?: ReactNode;
}

function candidateKey(candidate: ArtworkLookupCandidate): string {
  return candidate.external_id ?? candidate.object_url ?? candidate.title;
}

function lookupEndpoint(artworkId: number, params: LookupSearchParams = {}): string {
  const query = new URLSearchParams();
  query.set("source", "all");
  if (params.title?.trim()) {
    query.set("title_override", params.title.trim());
  }
  if (params.artist?.trim()) {
    query.set("artist_override", params.artist.trim());
  }
  if (params.searchMode === "broad") {
    query.set("search_mode", "broad");
  }
  return `/api/artworks/${artworkId}/lookup-image?${query.toString()}`;
}

function defaultApplyFields(
  artwork: Artwork,
  candidate: ArtworkLookupCandidate,
  preset: "image" | "image_title" | "title"
): ApplyFields {
  const suggestTitle = isPlaceholderTitle(artwork.title) && Boolean(candidate.title?.trim());
  return {
    image: preset === "image" || preset === "image_title",
    title: preset === "image_title" || preset === "title" || suggestTitle,
    artist: false,
    date: false,
    medium: false,
    sourceUrl: preset === "image" || preset === "image_title",
  };
}

function ApplyReview({
  artwork,
  pending,
  saving,
  onCancel,
  onConfirm,
  onToggle,
}: {
  artwork: Artwork;
  pending: PendingApply;
  saving: boolean;
  onCancel: () => void;
  onConfirm: () => void;
  onToggle: (field: keyof ApplyFields) => void;
}) {
  const { candidate, fields } = pending;

  const changes: string[] = [];
  if (fields.title && candidate.title && candidate.title !== artwork.title) {
    changes.push(`title from “${artwork.title || "Unknown"}” to “${candidate.title}”`);
  }
  if (fields.artist && candidate.artist && candidate.artist !== artwork.artist) {
    changes.push(`artist to “${candidate.artist}”`);
  }
  if (fields.date && candidate.date && candidate.date !== artwork.year_period) {
    changes.push(`date to “${candidate.date}”`);
  }
  if (fields.medium && candidate.medium && candidate.medium !== artwork.medium) {
    changes.push(`medium to “${candidate.medium}”`);
  }
  if (fields.image) {
    changes.push("official image");
  }
  if (fields.sourceUrl && candidate.object_url) {
    changes.push("catalog source URL");
  }

  const fieldOptions: { key: keyof ApplyFields; label: string; disabled?: boolean }[] = [
    { key: "image", label: "Image", disabled: !candidate.image_url },
    { key: "title", label: "Title", disabled: !candidate.title?.trim() },
    { key: "artist", label: "Artist", disabled: !candidate.artist?.trim() },
    { key: "date", label: "Date", disabled: !candidate.date?.trim() },
    { key: "medium", label: "Medium", disabled: !candidate.medium?.trim() },
    { key: "sourceUrl", label: "Source URL", disabled: !candidate.object_url },
  ];

  return (
    <div className="space-y-3 rounded-xl border border-border bg-muted/20 p-3">
      <p className="text-sm font-medium">Review before saving</p>
      {changes.length ? (
        <p className="text-xs leading-relaxed text-muted-foreground">
          Update {changes.join(", ")}?
        </p>
      ) : (
        <p className="text-xs text-muted-foreground">Select fields to apply.</p>
      )}
      <div className="flex flex-wrap gap-2">
        {fieldOptions.map(({ key, label, disabled }) => (
          <label
            key={key}
            className={cn(
              "inline-flex min-h-9 cursor-pointer items-center gap-2 rounded-lg border px-2.5 text-xs",
              fields[key] ? "border-primary bg-primary/5" : "border-border",
              disabled && "cursor-not-allowed opacity-50"
            )}
          >
            <input
              type="checkbox"
              className="size-3.5 accent-primary"
              checked={fields[key]}
              disabled={disabled || saving}
              onChange={() => onToggle(key)}
            />
            {label}
          </label>
        ))}
      </div>
      <div className="flex gap-2">
        <Button type="button" variant="outline" size="touch" className="flex-1" onClick={onCancel}>
          Cancel
        </Button>
        <Button
          type="button"
          size="touch"
          className="flex-1"
          disabled={saving || !Object.values(fields).some(Boolean)}
          onClick={onConfirm}
        >
          {saving ? "Saving…" : "Apply selected"}
        </Button>
      </div>
    </div>
  );
}

function LookupCandidateCard({
  candidate,
  artwork,
  applying,
  pendingKey,
  onPreset,
}: {
  candidate: ArtworkLookupCandidate;
  artwork: Artwork;
  applying: boolean;
  pendingKey: string | null;
  onPreset: (preset: "image" | "image_title" | "title") => void;
}) {
  const key = candidateKey(candidate);
  const busy = applying && pendingKey === key;
  const suggestTitle =
    isPlaceholderTitle(artwork.title) &&
    Boolean(candidate.title?.trim()) &&
    !candidate.low_confidence;

  return (
    <li
      className={cn(
        "rounded-xl border border-border bg-card p-3",
        candidate.low_confidence && "opacity-70"
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
            {candidate.low_confidence ? " · low confidence" : null}
          </p>
          {candidate.medium ? (
            <p className="text-[11px] text-muted-foreground">{candidate.medium}</p>
          ) : null}
          {suggestTitle ? (
            <p className="text-[11px] font-medium text-primary">Use this title?</p>
          ) : null}
        </div>
      </div>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
        <Button
          type="button"
          size="touch"
          variant="default"
          className="flex-1 sm:flex-none"
          disabled={!candidate.image_url || busy}
          onClick={() => onPreset("image")}
        >
          {busy ? "Saving…" : "Use image"}
        </Button>
        <Button
          type="button"
          size="touch"
          variant="secondary"
          className="flex-1 sm:flex-none"
          disabled={!candidate.image_url || !candidate.title?.trim() || busy}
          onClick={() => onPreset("image_title")}
        >
          Use image + update title
        </Button>
        <Button
          type="button"
          size="touch"
          variant="outline"
          className="flex-1 sm:flex-none"
          disabled={!candidate.title?.trim() || busy}
          onClick={() => onPreset("title")}
        >
          Update title only
        </Button>
        {candidate.object_url ? (
          <a
            href={candidate.object_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-h-11 items-center justify-center px-2 text-sm text-muted-foreground underline-offset-2 hover:underline"
          >
            View record
          </a>
        ) : null}
      </div>
    </li>
  );
}

/** Provider + lookup sheet. Mount once on the artwork detail page. */
export function ArtworkImageLookupPanel({
  artwork,
  canEdit,
  hasImage,
  aiTitleHint,
  aiArtistHint,
  onApplied,
  children,
}: ArtworkImageLookupPanelProps) {
  const [sheetOpen, setSheetOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [pendingKey, setPendingKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ArtworkLookupResponse | null>(null);
  const [manualTitle, setManualTitle] = useState("");
  const [manualArtist, setManualArtist] = useState("");
  const [pendingApply, setPendingApply] = useState<PendingApply | null>(null);

  const runAutoLookup = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResponse(null);
    setPendingApply(null);
    try {
      const result = await api.get<ArtworkLookupResponse>(lookupEndpoint(artwork.id));
      setResponse(result);
      if (!result.candidates.length && !result.query_used?.trim() && result.notice) {
        setError(result.notice);
      } else if (!result.candidates.length && !result.query_used?.trim()) {
        setError(MISSING_METADATA_HINT);
      } else if (!result.candidates.length && result.notice) {
        setError(result.notice);
      } else if (!result.candidates.length) {
        setError("No close matches found in the open collection indexes.");
      }
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Lookup failed. Check your connection and try again."
      );
      setResponse(null);
    } finally {
      setLoading(false);
    }
  }, [artwork.id]);

  const runManualLookup = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResponse(null);
    setPendingApply(null);
    try {
      const result = await api.get<ArtworkLookupResponse>(
        lookupEndpoint(artwork.id, {
          title: manualTitle || undefined,
          artist: manualArtist || undefined,
        })
      );
      setResponse(result);
      if (!result.candidates.length && !result.query_used?.trim() && result.notice) {
        setError(result.notice);
      } else if (!result.candidates.length && !result.query_used?.trim()) {
        setError(MISSING_METADATA_HINT);
      } else if (!result.candidates.length && result.notice) {
        setError(result.notice);
      } else if (!result.candidates.length) {
        setError("No close matches found in the open collection indexes.");
      }
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Lookup failed. Check your connection and try again."
      );
      setResponse(null);
    } finally {
      setLoading(false);
    }
  }, [artwork.id, manualArtist, manualTitle]);

  const runBroaderLookup = useCallback(async () => {
    setLoading(true);
    setError(null);
    setPendingApply(null);
    try {
      const result = await api.get<ArtworkLookupResponse>(
        lookupEndpoint(artwork.id, {
          title: manualTitle || undefined,
          artist: manualArtist || undefined,
          searchMode: "broad",
        })
      );
      setResponse(result);
      if (!result.candidates.length && result.notice) {
        setError(result.notice);
      } else if (!result.candidates.length) {
        setError("No matches found even with a broader search.");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lookup failed.");
    } finally {
      setLoading(false);
    }
  }, [artwork.id, manualArtist, manualTitle]);

  const openLookup = useCallback(() => {
    if (!canEdit) return;
    setManualTitle(isPlaceholderTitle(artwork.title) ? "" : artwork.title ?? "");
    setManualArtist(artwork.artist ?? "");
    setSheetOpen(true);
    void runAutoLookup();
  }, [artwork.artist, artwork.title, canEdit, runAutoLookup]);

  function startApply(candidate: ArtworkLookupCandidate, preset: "image" | "image_title" | "title") {
    setPendingApply({
      candidate,
      fields: defaultApplyFields(artwork, candidate, preset),
    });
    setPendingKey(candidateKey(candidate));
  }

  async function confirmApply() {
    if (!pendingApply) return;
    const { candidate, fields } = pendingApply;
    if (!Object.values(fields).some(Boolean)) return;

    setSaving(true);
    setError(null);
    try {
      const payload: Partial<Artwork> = {};
      if (fields.image && candidate.image_url) {
        payload.image_url = candidate.image_url;
        payload.image_thumbnail_url = candidate.image_thumbnail_url ?? candidate.image_url;
        payload.catalog_source = candidate.source_name;
        payload.catalog_accession_number = candidate.accession_number;
        payload.catalog_rights_label = candidate.rights_label;
      }
      if (fields.sourceUrl && candidate.object_url) {
        payload.catalog_object_url = candidate.object_url;
      }
      if (fields.title && candidate.title) {
        payload.title = candidate.title;
      }
      if (fields.artist && candidate.artist) {
        payload.artist = candidate.artist;
      }
      if (fields.date && candidate.date) {
        payload.year_period = candidate.date;
      }
      if (fields.medium && candidate.medium) {
        payload.medium = candidate.medium;
      }

      const updated = await api.put<Artwork>(`/api/artworks/${artwork.id}`, payload);
      onApplied(updated);
      setSheetOpen(false);
      setResponse(null);
      setPendingApply(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save changes.");
    } finally {
      setSaving(false);
      setPendingKey(null);
    }
  }

  const contextValue = useMemo(
    () => ({ openLookup, canEdit, hasImage }),
    [canEdit, hasImage, openLookup]
  );

  const highConfidence = response?.candidates.filter((c) => !c.low_confidence) ?? [];
  const lowConfidence = response?.candidates.filter((c) => c.low_confidence) ?? [];

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
            setPendingApply(null);
          }
        }}
        title={hasImage ? "Replace official image" : "Find official image"}
        description="Suggested matches from open museum collection records. Review before applying."
        footer={
          response?.candidates.length ? (
            <p className="text-center text-xs text-muted-foreground">
              {response.candidates.length} candidate{response.candidates.length === 1 ? "" : "s"}
            </p>
          ) : null
        }
      >
        <div className="space-y-4">
          {response?.query_used ? (
            <div className="rounded-lg border border-border bg-muted/30 px-3 py-2 text-xs">
              <p className="text-muted-foreground">
                Searching for:{" "}
                <span className="font-medium text-foreground">{response.query_used}</span>
              </p>
              <p className="mt-0.5 text-muted-foreground">
                Query source: {QUERY_SOURCE_LABELS[response.query_source] ?? response.query_source}
              </p>
              {response.query_strategy ? (
                <p className="mt-0.5 text-muted-foreground">
                  Match strategy:{" "}
                  {QUERY_STRATEGY_LABELS[response.query_strategy as ArtworkLookupQueryStrategy] ??
                    response.query_strategy}
                </p>
              ) : null}
              {response.sources_searched?.length ? (
                <p className="mt-0.5 text-muted-foreground">
                  Collections: {response.sources_searched.join(" · ")}
                </p>
              ) : null}
              {response.alternate_title ? (
                <button
                  type="button"
                  className="mt-1 text-primary underline-offset-2 hover:underline"
                  onClick={() => {
                    const title = response.alternate_title ?? "";
                    setManualTitle(title);
                    void (async () => {
                      setLoading(true);
                      setError(null);
                      setPendingApply(null);
                      try {
                        const result = await api.get<ArtworkLookupResponse>(
                          lookupEndpoint(artwork.id, {
                            title,
                            artist: manualArtist || undefined,
                          })
                        );
                        setResponse(result);
                      } catch (e) {
                        setError(e instanceof Error ? e.message : "Lookup failed.");
                      } finally {
                        setLoading(false);
                      }
                    })();
                  }}
                >
                  Also try: {response.alternate_title}
                </button>
              ) : null}
            </div>
          ) : null}

          <div className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
            <Input
              value={manualTitle}
              onChange={(event) => setManualTitle(event.target.value)}
              placeholder="Title"
              aria-label="Search title"
            />
            <Input
              value={manualArtist}
              onChange={(event) => setManualArtist(event.target.value)}
              placeholder="Artist"
              aria-label="Search artist"
            />
            <Button
              type="button"
              variant="outline"
              size="touch"
              className="sm:px-4"
              disabled={loading}
              onClick={() => void runManualLookup()}
            >
              Search again
            </Button>
          </div>

          {aiTitleHint && isPlaceholderTitle(artwork.title) ? (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="min-h-9 w-full sm:w-auto"
              disabled={loading}
              onClick={() => {
                setManualTitle(aiTitleHint);
                if (aiArtistHint) setManualArtist(aiArtistHint);
                void (async () => {
                  setLoading(true);
                  setError(null);
                  setPendingApply(null);
                  try {
                    const result = await api.get<ArtworkLookupResponse>(
                      lookupEndpoint(artwork.id, {
                        title: aiTitleHint,
                        artist:
                          aiArtistHint ??
                          (manualArtist || artwork.artist || undefined),
                      })
                    );
                    setResponse(result);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "Lookup failed.");
                  } finally {
                    setLoading(false);
                  }
                })();
              }}
            >
              Search using AI title
            </Button>
          ) : null}

          {loading ? (
            <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Searching collections…
            </div>
          ) : null}

          {response?.artist_fallback && response.notice ? (
            <p className="rounded-lg border border-amber-300/40 bg-amber-50 px-3 py-2 text-sm text-amber-950 dark:bg-amber-950/30 dark:text-amber-100">
              {response.notice}
            </p>
          ) : null}

          {error ? <p className="text-sm text-destructive">{error}</p> : null}

          {pendingApply ? (
            <ApplyReview
              artwork={artwork}
              pending={pendingApply}
              saving={saving}
              onCancel={() => {
                setPendingApply(null);
                setPendingKey(null);
              }}
              onConfirm={() => void confirmApply()}
              onToggle={(field) =>
                setPendingApply((current) =>
                  current
                    ? { ...current, fields: { ...current.fields, [field]: !current.fields[field] } }
                    : current
                )
              }
            />
          ) : null}

          {response?.disclaimer ? (
            <p className="text-xs leading-relaxed text-muted-foreground">{response.disclaimer}</p>
          ) : null}

          {!loading && highConfidence.length ? (
            <ul className="space-y-3">
              {highConfidence.map((candidate) => (
                <LookupCandidateCard
                  key={candidateKey(candidate)}
                  candidate={candidate}
                  artwork={artwork}
                  applying={saving}
                  pendingKey={pendingKey}
                  onPreset={(preset) => startApply(candidate, preset)}
                />
              ))}
            </ul>
          ) : null}

          {!loading && lowConfidence.length ? (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground">Lower confidence matches</p>
              <ul className="space-y-3">
                {lowConfidence.map((candidate) => (
                  <LookupCandidateCard
                    key={candidateKey(candidate)}
                    candidate={candidate}
                    artwork={artwork}
                    applying={saving}
                    pendingKey={pendingKey}
                    onPreset={(preset) => startApply(candidate, preset)}
                  />
                ))}
              </ul>
            </div>
          ) : null}

          {!loading && response && !response.candidates.length && !error ? (
            <div className="space-y-2">
              <p className="py-2 text-sm text-muted-foreground">
                No matches found. Adjust the title or artist above, or try a broader search.
              </p>
              <Button
                type="button"
                variant="secondary"
                size="touch"
                className="w-full"
                onClick={() => void runBroaderLookup()}
              >
                Try broader search
              </Button>
            </div>
          ) : null}

          {!loading && response?.candidates.length ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="min-h-9 w-full"
              onClick={() => void runBroaderLookup()}
            >
              Try broader search
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
    throw new Error("ArtworkImageLookupAction must be used within ArtworkImageLookupPanel.");
  }
  return context;
}

export { useArtworkImageLookup };

export interface ArtworkImageLookupActionProps {
  variant?: "find" | "replace";
  className?: string;
  fullWidth?: boolean;
  /** Primary image-area action (used in tests). */
  primary?: boolean;
}

/** Visible lookup trigger — always render for admin users on the detail page. */
export function ArtworkImageLookupAction({
  variant = "find",
  className,
  fullWidth = false,
  primary = false,
}: ArtworkImageLookupActionProps) {
  const { openLookup, canEdit, hasImage } = useArtworkImageLookup();

  if (!canEdit) {
    return null;
  }

  const isReplace = variant === "replace" || hasImage;
  const label = isReplace ? "Replace official image" : "Find official image";

  return (
    <Button
      type="button"
      variant="default"
      size="touch"
      data-testid={primary ? "artwork-official-image-lookup-primary" : undefined}
      className={cn("gap-2", fullWidth && "w-full", className)}
      onClick={openLookup}
    >
      {!isReplace ? <ImageIcon className="size-4" strokeWidth={1.75} /> : null}
      {label}
    </Button>
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
    <p
      data-testid="artwork-lookup-debug"
      className="mx-4 rounded border border-amber-300/60 bg-amber-50 px-2 py-1 font-mono text-[10px] text-amber-950 sm:mx-0"
    >
      lookup debug · isAdmin={String(canEdit)} · hasImage={String(hasImage)} · imageUrl=
      {imageUrl ? "yes" : "no"} · lookupMounted={lookupMounted ? "yes" : "no"}
    </p>
  );
}
