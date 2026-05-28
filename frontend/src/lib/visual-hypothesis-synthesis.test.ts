import { describe, expect, it } from "vitest";

import { synthesizeIdentificationFromDraft } from "@/lib/artwork-metadata";

describe("synthesizeIdentificationFromDraft", () => {
  it("builds an unverified hypothesis from legacy possible_title fields", () => {
    const identification = synthesizeIdentificationFromDraft({
      short_summary: "Four Dancers — possibly by Edgar Degas.",
      historical_context: "Degas ballet series.",
      visual_elements_to_notice: [],
      related_questions: [],
      possible_title: "Four Dancers",
      possible_artist: "Edgar Degas",
    });

    expect(identification).not.toBeNull();
    expect(identification?.identification_mode).toBe("style_subject");
    expect(identification?.visual_hypothesis_title).toBe("Four Dancers");
    expect(identification?.visual_hypothesis_artist).toBe("Edgar Degas");
    expect(identification?.display_summary).toContain("AI visual hypothesis");
    expect(identification?.display_summary).toContain("Not verified against collection records");
  });

  it("returns null when no title or artist hints exist", () => {
    expect(
      synthesizeIdentificationFromDraft({
        short_summary: "19th-century portrait tradition.",
        historical_context: "Context",
        visual_elements_to_notice: [],
        related_questions: [],
      })
    ).toBeNull();
  });
});
