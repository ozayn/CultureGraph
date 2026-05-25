import { describe, expect, it } from "vitest";

import { buildAnnotationTagSuggestions } from "@/lib/annotation-suggestions";
import type { CulturalEntity } from "@/lib/types";

describe("buildAnnotationTagSuggestions", () => {
  it("includes default examples and visit entity concepts", () => {
    const entities: CulturalEntity[] = [
      {
        id: 1,
        visit_id: 1,
        entity_type: "concept",
        name: "Ecological dread",
        description: null,
        themes: ["climate"],
        concepts: ["ecological collapse"],
        movements: [],
        historical_events: [],
        related_entities: [],
        image_url: null,
        thumbnail_url: null,
        image_source_name: null,
        image_source_url: null,
        image_rights_label: null,
        created_at: "2026-05-25T12:00:00Z",
      },
    ];

    const suggestions = buildAnnotationTagSuggestions(entities);

    expect(suggestions).toContain("composition");
    expect(suggestions).toContain("ecological collapse");
    expect(suggestions).toContain("climate");
    expect(suggestions).toContain("Ecological dread");
  });
});
