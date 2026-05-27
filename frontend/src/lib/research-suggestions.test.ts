import { describe, expect, it } from "vitest";

import {
  hasSuggestedCoordinates,
  inferAcceptedSuggestions,
  markSuggestionAccepted,
  normalizeAiSuggestedAnnotation,
  parseSuggestedAnnotations,
  pendingSuggestions,
  suggestedAnnotationToAnnotationPayload,
} from "@/lib/research-suggestions";
import type { Annotation } from "@/lib/types";

describe("research-suggestions", () => {
  it("parses structured AI suggestions from JSON", () => {
    const parsed = parseSuggestedAnnotations([
      {
        category: "material",
        note: "Notice the layered gesso ground.",
        tags: ["material"],
        linked_concept_names: ["labor"],
        confidence: 0.8,
        suggested_position: {
          x_percent: null,
          y_percent: null,
          reason: "Look for surface texture across the canvas.",
        },
      },
    ]);

    expect(parsed).toHaveLength(1);
    expect(parsed[0]?.category).toBe("material");
    expect(parsed[0]?.note).toContain("gesso");
    expect(hasSuggestedCoordinates(parsed[0]!)).toBe(false);
  });

  it("normalizes legacy text-only suggestions", () => {
    const item = normalizeAiSuggestedAnnotation({
      category: "observation",
      text: "Legacy note",
    });

    expect(item?.note).toBe("Legacy note");
    expect(item?.confidence).toBe(0.5);
  });

  it("defaults suggestion status to pending", () => {
    const item = normalizeAiSuggestedAnnotation({
      category: "observation",
      note: "A detail to notice.",
    });
    expect(item?.status).toBe("pending");
    expect(item?.accepted_annotation_id).toBeNull();
  });

  it("marks accepted suggestions as non-pending", () => {
    const pending = normalizeAiSuggestedAnnotation({
      category: "history",
      note: "Saved note",
    });
    expect(pending).not.toBeNull();

    const accepted = markSuggestionAccepted([pending!], pending!, 12);
    expect(pendingSuggestions(accepted)).toHaveLength(0);
  });

  it("infers accepted status from matching annotations", () => {
    const pending = normalizeAiSuggestedAnnotation({
      category: "symbol",
      note: "Recurring motif",
    });
    expect(pending).not.toBeNull();

    const annotations = [
      {
        id: 7,
        artwork_id: 1,
        x_percent: null,
        y_percent: null,
        category: "symbol",
        text: "Recurring motif",
        tags: [],
        linked_entity_ids: [],
        linked_concept_names: [],
        created_at: "2026-01-01T00:00:00Z",
      },
    ] satisfies Annotation[];

    const inferred = inferAcceptedSuggestions([pending!], annotations);
    expect(inferred[0]?.status).toBe("accepted");
    expect(inferred[0]?.accepted_annotation_id).toBe(7);
    expect(pendingSuggestions(inferred)).toHaveLength(0);
  });

  it("builds unplaced annotation payloads for accept", () => {
    const item = normalizeAiSuggestedAnnotation({
      category: "history",
      note: "Notice the layered gesso ground.",
      suggested_position: { x_percent: null, y_percent: null, reason: null },
    });
    expect(item).not.toBeNull();

    const payload = suggestedAnnotationToAnnotationPayload(item!);
    expect(payload.x_percent).toBeNull();
    expect(payload.y_percent).toBeNull();
    expect(payload.text).toContain("gesso");
  });
});
