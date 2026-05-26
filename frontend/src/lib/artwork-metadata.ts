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

export function isPlaceholderTitle(title: string | null | undefined): boolean {
  const normalized = (title ?? "").trim().toLowerCase();
  if (!normalized) return true;
  return PLACEHOLDER_TITLES.has(normalized);
}

export function isPlaceholderArtist(artist: string | null | undefined): boolean {
  const normalized = (artist ?? "").trim().toLowerCase();
  if (!normalized) return true;
  return PLACEHOLDER_ARTISTS.has(normalized);
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
  if (/^unknown\s*(period|date)?$/i.test(period)) return null;
  return period;
}

export interface ResearchMetadataHints {
  title: string | null;
  artist: string | null;
  period: string | null;
  confidence: number | null;
}

export function extractResearchMetadataHints(draft: {
  possible_title?: string | null;
  possible_artist?: string | null;
  period_or_movement?: string | null;
  confidence?: number | null;
  short_summary?: string | null;
}): ResearchMetadataHints | null {
  let title = cleanAiTitle(draft.possible_title);
  const artist = cleanAiArtist(draft.possible_artist);
  const period = cleanAiPeriod(draft.period_or_movement);

  if (!title && draft.short_summary) {
    title = cleanAiTitle(draft.short_summary.split(/\s*[—–-]\s*/)[0]);
  }

  if (!title && !artist && !period) return null;

  return {
    title,
    artist,
    period,
    confidence: draft.confidence ?? null,
  };
}
