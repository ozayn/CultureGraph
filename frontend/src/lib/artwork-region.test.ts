import { describe, expect, it } from "vitest";

import { clampArtworkRegion, DEFAULT_ARTWORK_REGION } from "@/lib/artwork-region";

describe("artwork-region", () => {
  it("clamps region inside image bounds", () => {
    const clamped = clampArtworkRegion({
      x_percent: 95,
      y_percent: 90,
      width_percent: 20,
      height_percent: 20,
    });
    expect(clamped.x_percent).toBeLessThanOrEqual(80);
    expect(clamped.y_percent).toBeLessThanOrEqual(80);
    expect(clamped.width_percent).toBeGreaterThanOrEqual(5);
  });

  it("provides a sensible default region", () => {
    expect(DEFAULT_ARTWORK_REGION.width_percent).toBeGreaterThan(50);
  });
});
