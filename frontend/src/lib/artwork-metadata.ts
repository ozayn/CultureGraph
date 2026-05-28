import type { ArtworkIdentification, ResearchDraft } from "@/lib/types";

const PLACEHOLDER_TITLES = new Set([
  "unknown",
  "untitled",
  "unidentified artwork",
  "unidentified",
  "painting",
  "artwork",
  "work",
  "no title",
  "untitled artwork",
]);

const PLACEHOLDER_ARTISTS = new Set([
  "unknown",
  "unknown artist",
  "unidentified",
  "anonymous",
  "attributed",
  "artist unknown",
]);

export const HIGH_CONFIDENCE_THRESHOLD = 0.95;
export const STRONG_CONFIDENCE_THRESHOLD = 0.80;
export const LOW_CONFIDENCE_THRESHOLD = 0.55;

export const UNKNOWN_ARTWORK_LABEL = "Unknown artwork";

export function isPlaceholderTitle(title: string | null | undefined): boolean {
  const normalized = (title ?? "").trim().toLowerCase();
  if (!normalized) return true;
  return PLACEHOLDER_TITLES.has(normalized);
}

/** Display label for artworks without a saved title (never stored in the DB). */
export function artworkDisplayTitle(title: string | null | undefined): string {
  if (isPlaceholderTitle(title)) return UNKNOWN_ARTWORK_LABEL;
  return title!.trim();
}

export function hasArtworkTitle(title: string | null | undefined): boolean {
  return !isPlaceholderTitle(title);
}

export function isPlaceholderArtist(artist: string | null | undefined): boolean {
  const normalized = (artist ?? "").trim().toLowerCase();
  if (!normalized) return true;
  return PLACEHOLDER_ARTISTS.has(normalized);
}

export function isPlaceholderNotes(notes: string | null | undefined): boolean {
  return !(notes ?? "").trim();
}

/** Strip attribution uncertainty from AI title strings. */
export function cleanAiTitle(raw: string | null | undefined): string | null {
  if (!raw?.trim()) return null;

  let title = raw.trim();
  title = title.split(/\s*[—–-]\s*(possibly|maybe|perhaps|attributed)/i)[0]?.trim() ?? title;
  title = title.replace(/\s*[—–-]\s*possibly by.+$/i, "").trim();
  title = title.replace(/\s*\((possibly|maybe|attributed)[^)]*\)/i, "").trim();

  if (!title || isPlaceholderTitle(title)) return null;
  return title;
}

/** Strip uncertainty prefixes from AI artist strings. */
export function cleanAiArtist(raw: string | null | undefined): string | null {
  if (!raw?.trim()) return null;

  let artist = raw.trim();
  artist = artist.replace(/^(possibly\s+by|possibly|maybe|perhaps|attributed to)\s+/i, "").trim();
  artist = artist.replace(/\s*\((possibly|maybe|attributed)[^)]*\)/i, "").trim();

  if (!artist || isPlaceholderArtist(artist)) return null;
  return artist;
}

export function cleanAiPeriod(raw: string | null | undefined): string | null {
  if (!raw?.trim()) return null;
  const period = raw.trim();
  if (/^unknown\s*(period|date|movement)?$/i.test(period)) return null;
  return period;
}

export function extractYearFromPeriod(raw: string | null | undefined): string | null {
  if (!raw?.trim()) return null;
  const text = raw.trim();
  const circa = text.match(/\bc\.?\s*(\d{3,4}s?)\b/i);
  if (circa) return `c. ${circa[1]}`;
  const range = text.match(/\b(\d{3,4})\s*[–-]\s*(\d{3,4})\b/);
  if (range) return `${range[1]}–${range[2]}`;
  const decade = text.match(/\b(\d{3,4}s)\b/i);
  if (decade) return decade[1];
  const year = text.match(/\b(1[0-9]{3}|20[0-9]{2})\b/);
  if (year) return year[1];
  return null;
}

export function extractMovementFromPeriod(raw: string | null | undefined): string | null {
  const cleaned = cleanAiPeriod(raw);
  if (!cleaned) return null;
  const withoutYear = cleaned
    .replace(/\bc\.?\s*\d{3,4}s?\b/gi, "")
    .replace(/\b\d{3,4}\s*[–-]\s*\d{3,4}\b/g, "")
    .replace(/\b(1[0-9]{3}|20[0-9]{2})s?\b/g, "")
    .replace(/[(),]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (!withoutYear || /^unknown$/i.test(withoutYear)) return null;
  return withoutYear;
}

const LOOKUP_MEDIUM_2D = [
  "painting",
  "pastel",
  "drawing",
  "print",
  "lithograph",
  "etching",
  "watercolor",
  "oil",
  "canvas",
  "paper",
  "charcoal",
];

const LOOKUP_MEDIUM_3D = [
  "sculpture",
  "statue",
  "bronze",
  "plaster",
  "plastiline",
  "armature",
  "cast",
  "marble",
  "beeswax",
  "figurine",
];

export type LookupMediumFilter = "2d" | "3d" | "any";

export function inferLookupMediumFilter(
  artworkMedium?: string | null,
  aiMedium?: string | null
): LookupMediumFilter {
  const text = [artworkMedium, aiMedium].filter(Boolean).join(" ").toLowerCase();
  if (!text.trim()) return "any";

  let score2d = 0;
  let score3d = 0;
  for (const keyword of LOOKUP_MEDIUM_2D) {
    if (text.includes(keyword)) score2d += 1;
  }
  for (const keyword of LOOKUP_MEDIUM_3D) {
    if (text.includes(keyword)) score3d += 1;
  }
  if (score3d > score2d && score3d > 0) return "3d";
  if (score2d > 0) return "2d";
  return "any";
}

export function lookupMediumFilterLabel(filter: LookupMediumFilter): string {
  if (filter === "2d") return "2D works";
  if (filter === "3d") return "3D works";
  return "Any type";
}

export function extractMediumFromDraft(draft: ResearchDraft): string | null {
  for (const item of draft.suggested_annotations ?? []) {
    if (item.category !== "material") continue;
    const note = item.note?.trim();
    if (note && note.length <= 255) return note;
  }
  return null;
}

export function extractNotesFromDraft(draft: ResearchDraft): string | null {
  const context = draft.historical_context?.trim();
  if (!context || context.length < 20) return null;
  return context.length > 1200 ? `${context.slice(0, 1197)}…` : context;
}

export interface ResearchMetadataHints {
  title: string | null;
  artist: string | null;
  lookupTitle?: string | null;
  lookupArtist?: string | null;
  year: string | null;
  period: string | null;
  medium: string | null;
  notes: string | null;
  confidence: number | null;
}

function hypothesisLookupTitle(
  draft: {
    visual_hypothesis_title?: string | null;
  },
  identification?: ArtworkIdentification | null
): string | null {
  if (identification?.identification_mode === "catalog_match") {
    return cleanAiTitle(identification.suggested_title ?? identification.catalog_title);
  }
  return cleanAiTitle(
    identification?.visual_hypothesis_title ?? draft.visual_hypothesis_title
  );
}

function hypothesisLookupArtist(
  draft: {
    visual_hypothesis_artist?: string | null;
  },
  identification?: ArtworkIdentification | null
): string | null {
  if (identification?.identification_mode === "catalog_match") {
    return cleanAiArtist(identification.suggested_artist ?? identification.catalog_artist);
  }
  return cleanAiArtist(
    identification?.visual_hypothesis_artist ?? draft.visual_hypothesis_artist
  );
}

export function extractResearchMetadataHints(
  draft: {
    possible_title?: string | null;
    possible_artist?: string | null;
    visual_hypothesis_title?: string | null;
    visual_hypothesis_artist?: string | null;
    period_or_movement?: string | null;
    confidence?: number | null;
    short_summary?: string | null;
    historical_context?: string | null;
    suggested_annotations?: ResearchDraft["suggested_annotations"];
  },
  identification?: ArtworkIdentification | null
): ResearchMetadataHints | null {
  const catalogMatch =
    identification?.identification_mode === "catalog_match" &&
    identification.confidence_level === "high";

  let title = catalogMatch
    ? cleanAiTitle(identification?.suggested_title ?? draft.possible_title)
    : null;
  let artist = catalogMatch
    ? cleanAiArtist(identification?.suggested_artist ?? draft.possible_artist)
    : null;

  const lookupTitle = hypothesisLookupTitle(draft, identification);
  const lookupArtist = hypothesisLookupArtist(draft, identification);

  if (!catalogMatch) {
    title = null;
    artist = null;
  }

  const year = extractYearFromPeriod(draft.period_or_movement);
  const period = extractMovementFromPeriod(draft.period_or_movement);
  const medium = draft.suggested_annotations
    ? extractMediumFromDraft(draft as ResearchDraft)
    : null;
  const notes = draft.historical_context
    ? extractNotesFromDraft(draft as ResearchDraft)
    : null;

  if (!title && draft.short_summary && catalogMatch) {
    title = cleanAiTitle(draft.short_summary.split(/\s*[—–-]\s*/)[0]);
  }

  if (!title && !artist && !lookupTitle && !lookupArtist && !year && !period && !medium && !notes) {
    return null;
  }

  const confidence =
    identification?.identity_certainty ??
    identification?.catalog_confidence ??
    draft.confidence ??
    (identification?.confidence_level === "high"
      ? HIGH_CONFIDENCE_THRESHOLD
      : identification?.confidence_level === "medium"
        ? STRONG_CONFIDENCE_THRESHOLD
        : null);

  return {
    title,
    artist,
    lookupTitle,
    lookupArtist,
    year,
    period,
    medium,
    notes,
    confidence,
  };
}

export function defaultMetadataFieldChecked(
  current: string | null | undefined,
  suggested: string | null,
  confidence: number | null,
  isPlaceholder: (value: string | null | undefined) => boolean
): boolean {
  if (!suggested?.trim()) return false;

  const hasUserValue = Boolean(current?.trim()) && !isPlaceholder(current);
  if (hasUserValue) return false;

  const level = confidence ?? 0.65;
  if (level < LOW_CONFIDENCE_THRESHOLD) return false;
  if (isPlaceholder(current) || !current?.trim()) return level >= STRONG_CONFIDENCE_THRESHOLD;
  return level >= HIGH_CONFIDENCE_THRESHOLD;
}

export function buildYearPeriodValue(
  year: string | null,
  period: string | null,
  applyYear: boolean,
  applyPeriod: boolean
): string | null {
  const parts: string[] = [];
  if (applyYear && year) parts.push(year);
  if (applyPeriod && period) parts.push(period);
  return parts.length ? parts.join(" · ") : null;
}

export function formatMetadataCurrent(value: string | null | undefined, fallback = "—"): string {
  const trimmed = (value ?? "").trim();
  return trimmed || fallback;
}

function parseTitleFromOcr(ocrText: string): string | null {
  const titleMatch = ocrText.match(/^(?:title|work)\s*:\s*(.+)$/im);
  if (titleMatch?.[1]) return cleanAiTitle(titleMatch[1]);
  const lines = ocrText
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines.length === 1 && lines[0].length >= 8) return cleanAiTitle(lines[0]);
  return null;
}

function parseArtistFromOcr(ocrText: string): string | null {
  const artistMatch = ocrText.match(/(?:artist|attributed to|by)\s*:\s*(.+)$/im);
  if (artistMatch?.[1]) return cleanAiArtist(artistMatch[1]);
  return null;
}

export function extractLabelMetadataHints(
  ocrText: string | null | undefined
): Pick<ResearchMetadataHints, "title" | "artist"> | null {
  const text = (ocrText ?? "").trim();
  if (!text) return null;

  const title = parseTitleFromOcr(text);
  const artist = parseArtistFromOcr(text);
  if (!title && !artist) return null;

  return { title, artist };
}
