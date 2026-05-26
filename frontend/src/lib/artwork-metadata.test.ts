import { describe, expect, it } from "vitest";

import {
  cleanAiArtist,
  cleanAiTitle,
  extractResearchMetadataHints,
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

  it("extracts metadata hints from research draft fields", () => {
    const hints = extractResearchMetadataHints({
      possible_title: "Four Dancers — possibly by Edgar Degas",
      possible_artist: "Edgar Degas",
      period_or_movement: "Impressionism",
      confidence: 0.82,
    });

    expect(hints?.title).toBe("Four Dancers");
    expect(hints?.artist).toBe("Edgar Degas");
    expect(hints?.period).toBe("Impressionism");
  });
});
