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

import { SignInInlineHint } from "@/components/auth/sign-in-inline-hint";
import { EntryThumbnail } from "@/components/ui/entry-thumbnail";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import {
  inferLookupMediumFilter,
  isPlaceholderTitle,
  lookupMediumFilterLabel,
  type LookupMediumFilter,
} from "@/lib/artwork-metadata";
import { museumCollectionSearchLabel } from "@/lib/museum-collection";
import type {
  Artwork,
  ArtworkLookupCandidate,
  ArtworkLookupMediumFilter,
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
  ocr_label: "Wall label (OCR)",
  visual_keywords: "Visual keywords",
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
  mediumType?: ArtworkLookupMediumFilter;
  broadenSources?: boolean;
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
  openLookup: (params?: LookupSearchParams) => void;
  canEdit: boolean;
  hasImage: boolean;
}

const ArtworkImageLookupContext = createContext<ArtworkImageLookupContextValue | null>(null);

export interface ArtworkImageLookupPanelProps {
  artwork: Artwork;
  canEdit: boolean;
  hasImage: boolean;
  visitMuseumName?: string | null;
  aiTitleHint?: string | null;
  aiArtistHint?: string | null;
  aiMediumHint?: string | null;
  onApplied: (artwork: Artwork) => void;
  children?: ReactNode;
}

function candidateKey(candidate: ArtworkLookupCandidate): string {
  return candidate.external_id ?? candidate.object_url ?? candidate.title;
}

function lookupEndpoint(artworkId: number, params: LookupSearchParams = {}): string {
  const query = new URLSearchParams();
  if (params.broadenSources) {
    query.set("broaden_sources", "true");
  }
  if (params.title?.trim()) {
    query.set("title_override", params.title.trim());
  }
  if (params.artist?.trim()) {
    query.set("artist_override", params.artist.trim());
  }
  if (params.searchMode === "broad") {
    query.set("search_mode", "broad");
  }
  if (params.mediumType && params.mediumType !== "any") {
    query.set("medium_type", params.mediumType);
  }
  const queryString = query.toString();
  return `/api/artworks/${artworkId}/lookup-image${queryString ? `?${queryString}` : ""}`;
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
        (candidate.low_confidence || candidate.medium_match === false) && "opacity-70"
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
            <p className="text-[11px] text-muted-foreground">
              {candidate.medium_type === "2d"
                ? "2D · "
                : candidate.medium_type === "3d"
                  ? "3D · "
                  : null}
              {candidate.medium}
            </p>
          ) : candidate.medium_type && candidate.medium_type !== "unknown" ? (
            <p className="text-[11px] text-muted-foreground">
              {candidate.medium_type === "2d" ? "2D work" : "3D work"}
            </p>
          ) : null}
          {candidate.match_reasons?.length ? (
            <p className="text-[11px] text-muted-foreground">
              {candidate.match_reasons.join(" · ")}
            </p>
          ) : null}
          {candidate.medium_match === false ? (
            <p className="text-[11px] font-medium text-amber-800 dark:text-amber-200">
              Different object type than your artwork
            </p>
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
  visitMuseumName = null,
  aiTitleHint,
  aiArtistHint,
  aiMediumHint,
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
  const defaultMediumFilter = useMemo(
    () => inferLookupMediumFilter(artwork.medium, aiMediumHint),
    [aiMediumHint, artwork.medium]
  );
  const [mediumTypeFilter, setMediumTypeFilter] =
    useState<LookupMediumFilter>(defaultMediumFilter);
  const collectionLabel = response?.museum_collection_name ?? visitMuseumName ?? null;
  const searchingLabel =
    response?.search_scope === "broad"
      ? "Searching open museum collections"
      : museumCollectionSearchLabel(collectionLabel) ?? "Searching museum collection";

  const fetchLookup = useCallback(
    async (params: LookupSearchParams = {}) => {
      setLoading(true);
      setError(null);
      setResponse(null);
      setPendingApply(null);
      try {
        const result = await api.get<ArtworkLookupResponse>(
          lookupEndpoint(artwork.id, {
            mediumType: params.mediumType ?? mediumTypeFilter,
            title: params.title,
            artist: params.artist,
            searchMode: params.searchMode,
            broadenSources: params.broadenSources,
          })
        );
        setResponse(result);
        if (result.medium_type_filter) {
          setMediumTypeFilter(result.medium_type_filter as LookupMediumFilter);
        }
        if (!result.candidates.length && !result.query_used?.trim() && result.notice) {
          setError(result.notice);
        } else if (!result.candidates.length && !result.query_used?.trim()) {
          setError(MISSING_METADATA_HINT);
        } else if (!result.candidates.length && result.notice) {
          setError(result.notice);
        } else if (!result.candidates.length) {
          setError(
            result.search_scope === "broad"
              ? "No close matches found across open collections."
              : collectionLabel
                ? `No close matches found in the ${collectionLabel} collection.`
                : "No close matches found in the selected museum collection."
          );
        }
      } catch (e) {
        setError(
          e instanceof Error ? e.message : "Lookup failed. Check your connection and try again."
        );
        setResponse(null);
      } finally {
        setLoading(false);
      }
    },
    [artwork.id, collectionLabel, mediumTypeFilter]
  );

  const runAutoLookup = useCallback(
    (mediumType?: LookupMediumFilter) => fetchLookup({ mediumType }),
    [fetchLookup]
  );

  const runManualLookup = useCallback(
    () =>
      fetchLookup({
        title: manualTitle || undefined,
        artist: manualArtist || undefined,
      }),
    [fetchLookup, manualArtist, manualTitle]
  );

  const runBroadenLookup = useCallback(
    async () => {
      setLoading(true);
      setError(null);
      setPendingApply(null);
      try {
        const result = await api.get<ArtworkLookupResponse>(
          lookupEndpoint(artwork.id, {
            mediumType: mediumTypeFilter,
            title: manualTitle || undefined,
            artist: manualArtist || undefined,
            broadenSources: true,
          })
        );
        setResponse(result);
        if (!result.candidates.length && result.notice) {
          setError(result.notice);
        } else if (!result.candidates.length) {
          setError("No matches found even with a broadened search.");
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Lookup failed.");
      } finally {
        setLoading(false);
      }
    },
    [artwork.id, manualArtist, manualTitle, mediumTypeFilter]
  );

  const openLookup = useCallback(
    (params?: LookupSearchParams) => {
      if (!canEdit) return;
      const titleHint = params?.title?.trim() || (isPlaceholderTitle(artwork.title) ? "" : artwork.title ?? "");
      const artistHint = params?.artist?.trim() || artwork.artist || "";
      setManualTitle(titleHint);
      setManualArtist(artistHint);
      const inferred = inferLookupMediumFilter(artwork.medium, aiMediumHint);
      setMediumTypeFilter(inferred);
      setSheetOpen(true);
      if (params?.title || params?.artist) {
        void fetchLookup({
          title: params.title,
          artist: params.artist,
          mediumType: inferred,
        });
      } else {
        void runAutoLookup(inferred);
      }
    },
    [
      aiMediumHint,
      artwork.artist,
      artwork.medium,
      artwork.title,
      canEdit,
      fetchLookup,
      runAutoLookup,
    ]
  );

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
        const displayUrl = candidate.image_url;
        const thumbUrl = candidate.image_thumbnail_url ?? candidate.image_url;
        payload.image_url = displayUrl;
        payload.image_thumbnail_url = thumbUrl;
        payload.catalog_image_url = displayUrl;
        payload.catalog_thumbnail_url = thumbUrl;
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

  const likelyMatches =
    response?.candidates.filter(
      (c) => !c.low_confidence && c.medium_match !== false
    ) ?? [];
  const lowConfidence =
    response?.candidates.filter(
      (c) => c.low_confidence && c.medium_match !== false
    ) ?? [];
  const mediumMismatches =
    response?.candidates.filter((c) => c.medium_match === false) ?? [];

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
        description={
          response?.search_scope === "broad"
            ? "Suggested matches from open museum collection records. Review before applying."
            : collectionLabel
              ? `Suggested matches from the ${collectionLabel} collection. Review before applying.`
              : "Suggested matches from museum collection records. Review before applying."
        }
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
                    void fetchLookup({
                      title,
                      artist: manualArtist || undefined,
                    });
                  }}
                >
                  Also try: {response.alternate_title}
                </button>
              ) : null}
            </div>
          ) : null}

          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Type</p>
            <div className="flex flex-wrap gap-2">
              {(["2d", "3d", "any"] as const).map((value) => (
                <Button
                  key={value}
                  type="button"
                  size="sm"
                  variant={mediumTypeFilter === value ? "default" : "outline"}
                  className="min-h-9"
                  disabled={loading}
                  onClick={() => {
                    setMediumTypeFilter(value);
                    void fetchLookup({
                      mediumType: value,
                      title: manualTitle || undefined,
                      artist: manualArtist || undefined,
                    });
                  }}
                >
                  {lookupMediumFilterLabel(value)}
                </Button>
              ))}
            </div>
            {response?.expected_medium_type &&
            response.expected_medium_type !== "unknown" ? (
              <p className="text-[11px] text-muted-foreground">
                Inferred from your artwork:{" "}
                {response.expected_medium_type === "2d" ? "2D work" : "3D work"}
              </p>
            ) : null}
          </div>

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
                void fetchLookup({
                  title: aiTitleHint,
                  artist:
                    aiArtistHint ?? (manualArtist || artwork.artist || undefined),
                });
              }}
            >
              Search using AI visual hypothesis
            </Button>
          ) : null}

          {loading ? (
            <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              {searchingLabel}…
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

          {!loading && likelyMatches.length ? (
            <ul className="space-y-3">
              {likelyMatches.map((candidate) => (
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

          {!loading && mediumMismatches.length ? (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground">Less likely matches</p>
              <p className="text-[11px] text-muted-foreground">
                Different object type (e.g. sculpture vs painting) — shown for review.
              </p>
              <ul className="space-y-3">
                {mediumMismatches.map((candidate) => (
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
                No matches found. Adjust the title or artist above, or broaden the search to other
                open collections.
              </p>
              {response.search_scope !== "broad" ? (
                <Button
                  type="button"
                  variant="secondary"
                  size="touch"
                  className="w-full"
                  onClick={() => void runBroadenLookup()}
                >
                  Broaden search
                </Button>
              ) : null}
            </div>
          ) : null}

          {!loading && response?.candidates.length && response.search_scope !== "broad" ? (
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="min-h-9 w-full"
              onClick={() => void runBroadenLookup()}
            >
              Broaden search
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
      onClick={() => openLookup()}
    >
      {!isReplace ? <ImageIcon className="size-4" strokeWidth={1.75} /> : null}
      {label}
    </Button>
  );
}

/** @deprecated Use SignInInlineHint with hint="officialImage". */
export function ArtworkImageLookupSignInHint({ className }: { className?: string }) {
  return <SignInInlineHint hint="officialImage" className={className} />;
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
