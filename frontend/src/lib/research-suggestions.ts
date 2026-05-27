import type { AnnotationPinFormValues } from "@/lib/annotation-form";
import type {
  AiSuggestedAnnotation,
  Annotation,
  AnnotationCategory,
  SuggestedAnnotationStatus,
} from "@/lib/types";

const VALID_CATEGORIES = new Set<AnnotationCategory>([
  "observation",
  "symbol",
  "history",
  "question",
  "composition",
  "material",
]);

function normalizeCategory(value: unknown): AnnotationCategory {
  if (typeof value === "string" && VALID_CATEGORIES.has(value as AnnotationCategory)) {
    return value as AnnotationCategory;
  }
  return "observation";
}

function normalizeStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.map(String).filter(Boolean);
}

function normalizeStatus(value: unknown): SuggestedAnnotationStatus {
  if (value === "accepted" || value === "dismissed" || value === "pending") {
    return value;
  }
  return "pending";
}

export function suggestionMatchKey(suggestion: Pick<AiSuggestedAnnotation, "category" | "note">): string {
  const note = suggestion.note.trim().toLowerCase().replace(/\s+/g, " ");
  return `${suggestion.category}::${note}`;
}

export function pendingSuggestions(suggestions: AiSuggestedAnnotation[]): AiSuggestedAnnotation[] {
  return suggestions.filter((item) => normalizeStatus(item.status) === "pending");
}

export function inferAcceptedSuggestions(
  suggestions: AiSuggestedAnnotation[],
  annotations: Annotation[]
): AiSuggestedAnnotation[] {
  if (suggestions.length === 0 || annotations.length === 0) return suggestions;

  const byKey = new Map<string, Annotation>();
  for (const annotation of annotations) {
    byKey.set(suggestionMatchKey({ category: annotation.category, note: annotation.text }), annotation);
  }

  let changed = false;
  const updated = suggestions.map((suggestion) => {
    const status = normalizeStatus(suggestion.status);
    if (status === "accepted" || status === "dismissed") {
      return suggestion;
    }

    const match = byKey.get(suggestionMatchKey(suggestion));
    if (!match) {
      return { ...suggestion, status: "pending" as const, accepted_annotation_id: null };
    }

    changed = true;
    return {
      ...suggestion,
      status: "accepted" as const,
      accepted_annotation_id: match.id,
    };
  });

  return changed ? updated : suggestions;
}

export function markSuggestionAccepted(
  suggestions: AiSuggestedAnnotation[],
  target: AiSuggestedAnnotation,
  annotationId: number
): AiSuggestedAnnotation[] {
  const key = suggestionMatchKey(target);
  return suggestions.map((item) =>
    suggestionMatchKey(item) === key
      ? { ...item, status: "accepted" as const, accepted_annotation_id: annotationId }
      : item
  );
}

export function markSuggestionDismissed(
  suggestions: AiSuggestedAnnotation[],
  target: AiSuggestedAnnotation
): AiSuggestedAnnotation[] {
  const key = suggestionMatchKey(target);
  return suggestions.map((item) =>
    suggestionMatchKey(item) === key
      ? { ...item, status: "dismissed" as const, accepted_annotation_id: null }
      : item
  );
}

function normalizePosition(raw: unknown): AiSuggestedAnnotation["suggested_position"] {
  if (!raw || typeof raw !== "object") {
    return { x_percent: null, y_percent: null, reason: null };
  }
  const position = raw as Record<string, unknown>;
  const x =
    typeof position.x_percent === "number" ? position.x_percent : null;
  const y =
    typeof position.y_percent === "number" ? position.y_percent : null;
  if (x === null || y === null) {
    return {
      x_percent: null,
      y_percent: null,
      reason: typeof position.reason === "string" ? position.reason : null,
    };
  }
  return {
    x_percent: x,
    y_percent: y,
    reason: typeof position.reason === "string" ? position.reason : null,
  };
}

export function normalizeAiSuggestedAnnotation(raw: unknown): AiSuggestedAnnotation | null {
  if (!raw || typeof raw !== "object") return null;
  const item = raw as Record<string, unknown>;
  const note =
    typeof item.note === "string"
      ? item.note
      : typeof item.text === "string"
        ? item.text
        : "";
  if (!note.trim()) return null;

  const status = normalizeStatus(item.status);
  const acceptedId = item.accepted_annotation_id;

  return {
    category: normalizeCategory(item.category),
    note: note.trim(),
    tags: normalizeStringList(item.tags),
    linked_concept_names: normalizeStringList(item.linked_concept_names),
    confidence:
      typeof item.confidence === "number"
        ? Math.min(1, Math.max(0, item.confidence))
        : 0.5,
    suggested_position: normalizePosition(item.suggested_position),
    status,
    accepted_annotation_id:
      status === "accepted" && typeof acceptedId === "number" ? acceptedId : null,
  };
}

export function parseSuggestedAnnotations(value: unknown): AiSuggestedAnnotation[] {
  if (Array.isArray(value)) {
    return value
      .map((item) => normalizeAiSuggestedAnnotation(item))
      .filter((item): item is AiSuggestedAnnotation => item !== null);
  }

  if (typeof value !== "string" || !value.trim()) return [];

  try {
    const parsed = JSON.parse(value) as unknown;
    if (Array.isArray(parsed)) {
      return parseSuggestedAnnotations(parsed);
    }
  } catch {
    // fall through to legacy line parsing
  }

  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [category, ...rest] = line.split(" — ");
      return normalizeAiSuggestedAnnotation({
        category: category || "observation",
        note: rest.join(" — ") || line,
        confidence: 0.5,
        suggested_position: { x_percent: null, y_percent: null, reason: null },
      });
    })
    .filter((item): item is AiSuggestedAnnotation => item !== null);
}

export function hasSuggestedCoordinates(
  suggestion: AiSuggestedAnnotation
): suggestion is AiSuggestedAnnotation & {
  suggested_position: { x_percent: number; y_percent: number };
} {
  return (
    suggestion.suggested_position.x_percent !== null &&
    suggestion.suggested_position.y_percent !== null
  );
}

export function suggestedAnnotationToFormValues(
  suggestion: AiSuggestedAnnotation
): AnnotationPinFormValues {
  return {
    category: suggestion.category,
    text: suggestion.note,
    tags: suggestion.tags,
    linkedEntityIds: [],
    linkedConceptNames: suggestion.linked_concept_names,
  };
}

export function formValuesToSuggestedAnnotation(
  values: AnnotationPinFormValues,
  existing: AiSuggestedAnnotation
): AiSuggestedAnnotation {
  return {
    ...existing,
    category: values.category,
    note: values.text.trim(),
    tags: values.tags,
    linked_concept_names: values.linkedConceptNames,
  };
}

export function suggestedAnnotationToAnnotationPayload(
  suggestion: AiSuggestedAnnotation,
  position?: { x_percent: number; y_percent: number } | null
) {
  let x_percent: number | null = null;
  let y_percent: number | null = null;

  if (position) {
    x_percent = position.x_percent;
    y_percent = position.y_percent;
  } else if (hasSuggestedCoordinates(suggestion)) {
    x_percent = suggestion.suggested_position.x_percent;
    y_percent = suggestion.suggested_position.y_percent;
  }

  return {
    x_percent,
    y_percent,
    category: suggestion.category,
    text: suggestion.note,
    tags: suggestion.tags,
    linked_entity_ids: [] as number[],
    linked_concept_names: suggestion.linked_concept_names,
  };
}
