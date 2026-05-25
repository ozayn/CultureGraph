import type { CulturalEntity } from "@/lib/types";

export const DEFAULT_ANNOTATION_TAG_SUGGESTIONS = [
  "composition",
  "gesture",
  "colonialism",
  "migration",
  "labor",
  "material",
  "ecological collapse",
  "American identity",
] as const;

function normalizeTag(value: string): string {
  return value.trim().replace(/\s+/g, " ");
}

export function buildAnnotationTagSuggestions(
  culturalEntities: CulturalEntity[]
): string[] {
  const suggestions = new Set<string>(DEFAULT_ANNOTATION_TAG_SUGGESTIONS);

  for (const entity of culturalEntities) {
    if (entity.name.trim()) suggestions.add(normalizeTag(entity.name));
    for (const value of [
      ...entity.themes,
      ...entity.concepts,
      ...entity.movements,
      ...entity.historical_events,
      ...entity.related_entities,
    ]) {
      if (value.trim()) suggestions.add(normalizeTag(value));
    }
  }

  return Array.from(suggestions).sort((left, right) =>
    left.localeCompare(right, undefined, { sensitivity: "base" })
  );
}

export function normalizeAnnotationTags(tags: string[]): string[] {
  const seen = new Set<string>();
  const normalized: string[] = [];

  for (const tag of tags) {
    const value = normalizeTag(tag);
    if (!value) continue;
    const key = value.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    normalized.push(value);
  }

  return normalized;
}

export function normalizeConceptNames(names: string[]): string[] {
  return normalizeAnnotationTags(names);
}
