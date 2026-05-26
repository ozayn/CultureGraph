import { describe, expect, it } from "vitest";

import {
  buildYearPeriodValue,
  cleanAiArtist,
  cleanAiTitle,
  defaultMetadataFieldChecked,
  extractMovementFromPeriod,
  extractResearchMetadataHints,
  extractYearFromPeriod,
  isPlaceholderTitle,
} from "@/lib/artwork-metadata";

describe("artwork-metadata", () => {
  it("treats Unknown as a placeholder title", () => {
    expect(isPlaceholderTitle("Unknown")).toBe(true);
    expect(isPlaceholderTitle("Four Dancers")).toBe(false);
  });

  it("cleans uncertain wording from AI titles", () => {
    expect(cleanAiTitle("Four Dancers — possibly by Edgar Degas")).toBe("Four Dancers");
    expect(cleanAiTitle("Four Dancers (possibly attributed)")).toBe("Four Dancers");
  });

  it("cleans uncertain wording from AI artists", () => {
    expect(cleanAiArtist("possibly by Edgar Degas")).toBe("Edgar Degas");
    expect(cleanAiArtist("Edgar Degas")).toBe("Edgar Degas");
  });

  it("extracts year and movement from period_or_movement", () => {
    expect(extractYearFromPeriod("Impressionism, c. 1890")).toBe("c. 1890");
    expect(extractMovementFromPeriod("Impressionism, c. 1890")).toBe("Impressionism");
    expect(buildYearPeriodValue("c. 1890", "Impressionism", true, true)).toBe(
      "c. 1890 · Impressionism"
    );
  });

  it("extracts metadata hints from research draft fields", () => {
    const hints = extractResearchMetadataHints({
      possible_title: "Four Dancers — possibly by Edgar Degas",
      possible_artist: "Edgar Degas",
      period_or_movement: "Impressionism, c. 1890",
      confidence: 0.82,
      historical_context: "A rehearsal scene from Degas's ballet series.",
      suggested_annotations: [
        {
          category: "material",
          note: "Pastel on paper",
          tags: [],
          linked_concept_names: [],
          confidence: 0.8,
          suggested_position: { x_percent: null, y_percent: null, reason: null },
        },
      ],
    });

    expect(hints?.title).toBe("Four Dancers");
    expect(hints?.artist).toBe("Edgar Degas");
    expect(hints?.year).toBe("c. 1890");
    expect(hints?.period).toBe("Impressionism");
    expect(hints?.medium).toBe("Pastel on paper");
    expect(hints?.notes).toContain("rehearsal scene");
  });

  it("defaults checked for empty fields with high confidence", () => {
    expect(
      defaultMetadataFieldChecked("Unknown", "Four Dancers", 0.85, isPlaceholderTitle)
    ).toBe(true);
    expect(
      defaultMetadataFieldChecked("Brooklyn Bridge", "Four Dancers", 0.85, isPlaceholderTitle)
    ).toBe(false);
    expect(
      defaultMetadataFieldChecked("Unknown", "Four Dancers", 0.4, isPlaceholderTitle)
    ).toBe(false);
  });
});
