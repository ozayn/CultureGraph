"use client";

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ArtworkEnrichmentPanel } from "@/components/artworks/artwork-enrichment-panel";
import type { Artwork } from "@/lib/types";

const getMock = vi.fn();

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    api: {
      get: (...args: unknown[]) => getMock(...args),
      put: vi.fn(),
      post: vi.fn(),
      delete: vi.fn(),
    },
  };
});

vi.mock("next/navigation", () => ({
  usePathname: () => "/artworks/535",
}));

vi.mock("@/components/artworks/research-metadata-apply", () => ({
  ResearchMetadataApply: () => null,
  extractDraftMetadataHints: () => null,
}));

vi.mock("@/components/artworks/enrichment-lookup-candidates", () => ({
  LookupCandidateList: () => null,
}));

vi.mock("@/components/artworks/ai-suggested-annotations", () => ({
  AiSuggestedAnnotations: () => null,
}));

vi.mock("@/components/artworks/artwork-identification-panel", () => ({
  ArtworkIdentificationPanel: ({
    identification,
  }: {
    identification: {
      visual_hypothesis_title?: string | null;
      visual_hypothesis_artist?: string | null;
      display_summary: string;
    };
  }) => (
    <div>
      <p>AI visual hypothesis</p>
      <p>{identification.visual_hypothesis_title}</p>
      <p>{identification.visual_hypothesis_artist}</p>
      <p>{identification.display_summary}</p>
    </div>
  ),
}));

const artwork: Artwork = {
  id: 535,
  visit_id: 1,
  title: "Unknown",
  artist: null,
  year_period: null,
  medium: null,
  museum_gallery: null,
  image_url: "/uploads/artworks/535/display.webp",
  image_thumbnail_url: null,
  image_width: null,
  image_height: null,
  image_mime_type: null,
  image_file_size: null,
  captured_at: null,
  captured_date_source: "none",
  catalog_source: null,
  catalog_object_url: null,
  catalog_accession_number: null,
  catalog_rights_label: null,
  personal_notes: null,
  created_at: "2026-05-25T12:00:00Z",
};

describe("ArtworkEnrichmentPanel legacy hypothesis fallback", () => {
  afterEach(() => {
    cleanup();
    getMock.mockReset();
  });

  it("renders AI visual hypothesis from draft when identification is missing", async () => {
    getMock.mockResolvedValue({
      status: "completed",
      stage: null,
      error: null,
      research_note_id: 66,
      identification: null,
      lookup: null,
      draft: {
        short_summary: "Four Dancers — possibly by Edgar Degas.",
        historical_context: "Short.",
        visual_elements_to_notice: [],
        related_questions: [],
        possible_title: "Four Dancers",
        possible_artist: "Edgar Degas",
      },
    });

    render(
      <ArtworkEnrichmentPanel artwork={artwork} canEdit hasImage onArtworkUpdated={vi.fn()} />
    );

    await waitFor(() => {
      expect(screen.getByText("AI visual hypothesis")).toBeInTheDocument();
      expect(screen.getByText("Four Dancers")).toBeInTheDocument();
      expect(screen.getByText("Edgar Degas")).toBeInTheDocument();
      expect(
        screen.getByText(/Not verified against collection records/)
      ).toBeInTheDocument();
    });
  });
});
