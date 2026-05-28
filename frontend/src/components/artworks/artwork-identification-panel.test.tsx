import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ArtworkIdentificationPanel } from "@/components/artworks/artwork-identification-panel";
import type { ArtworkIdentification } from "@/lib/types";

vi.mock("@/components/artworks/artwork-image-lookup-panel", () => ({
  useArtworkImageLookup: () => ({ openLookup: vi.fn() }),
}));

describe("ArtworkIdentificationPanel visual tags", () => {
  it("shows extracted visual tags for match transparency", () => {
    const identification: ArtworkIdentification = {
      identification_mode: "style_subject",
      confidence_level: "low",
      display_summary: "AI visual hypothesis: Four Dancers by Edgar Degas.",
      visual_tags: ["ballet", "dancers", "pastel", "Degas-like"],
      match_reasons: [],
    };

    render(<ArtworkIdentificationPanel identification={identification} canEdit={false} />);

    expect(screen.getByText("Visual tags")).toBeInTheDocument();
    expect(screen.getByText("ballet")).toBeInTheDocument();
    expect(screen.getByText("Degas-like")).toBeInTheDocument();
    expect(
      screen.getByText(/These distinctive cues informed collection search/)
    ).toBeInTheDocument();
  });
});
