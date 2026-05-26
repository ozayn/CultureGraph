import { describe, expect, it } from "vitest";

import {
  hasSuggestedCoordinates,
  normalizeAiSuggestedAnnotation,
  parseSuggestedAnnotations,
  suggestedAnnotationToAnnotationPayload,
} from "@/lib/research-suggestions";

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
