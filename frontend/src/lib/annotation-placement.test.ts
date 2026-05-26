import { describe, expect, it } from "vitest";

import { splitAnnotationsByPlacement } from "@/lib/annotation-placement";
import type { Annotation } from "@/lib/types";

describe("annotation-placement", () => {
  it("splits placed and unplaced annotations", () => {
    const annotations: Annotation[] = [
      {
        id: 1,
        artwork_id: 1,
        x_percent: 10,
        y_percent: 20,
        category: "observation",
        text: "Placed",
        tags: [],
        linked_entity_ids: [],
        linked_concept_names: [],
        created_at: "2026-05-25T12:00:00Z",
      },
      {
        id: 2,
        artwork_id: 1,
        x_percent: null,
        y_percent: null,
        category: "history",
        text: "Unplaced",
        tags: [],
        linked_entity_ids: [],
        linked_concept_names: [],
        created_at: "2026-05-25T12:00:00Z",
      },
    ];

    const { placed, unplaced } = splitAnnotationsByPlacement(annotations);
    expect(placed).toHaveLength(1);
    expect(unplaced).toHaveLength(1);
    expect(unplaced[0]?.text).toBe("Unplaced");
  });
});
