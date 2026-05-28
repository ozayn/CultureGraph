"use client";

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ResearchMetadataApply } from "@/components/artworks/research-metadata-apply";
import type { Artwork, ResearchDraft } from "@/lib/types";

const putMock = vi.fn();

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    api: {
      get: vi.fn(),
      put: (...args: unknown[]) => putMock(...args),
      post: vi.fn(),
      delete: vi.fn(),
    },
  };
});

vi.mock("@/components/artworks/artwork-image-lookup-panel", () => ({
  useArtworkImageLookup: () => ({
    openLookup: vi.fn(),
    hasImage: false,
  }),
}));

const artwork: Artwork = {
  id: 12,
  visit_id: 3,
  title: "Unknown",
  artist: null,
  year_period: null,
  medium: null,
  museum_gallery: null,
  image_url: null,
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

const legacyDraft: ResearchDraft = {
  short_summary: "Four Dancers — possibly by Edgar Degas.",
  historical_context: "Short.",
  visual_elements_to_notice: [],
  related_questions: [],
  possible_title: "Four Dancers",
  possible_artist: "Edgar Degas",
};

describe("ResearchMetadataApply working hypothesis actions", () => {
  afterEach(() => {
    cleanup();
    putMock.mockReset();
  });

  it("labels unverified AI guesses as working metadata", () => {
    render(
      <ResearchMetadataApply
        artwork={artwork}
        draft={legacyDraft}
        identification={null}
        canEdit
        onApplied={vi.fn()}
      />
    );

    expect(screen.getByText("AI visual hypothesis")).toBeInTheDocument();
    expect(
      screen.getByText(/Working metadata only — not verified against collection records/)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Use as working title" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Use as working artist" })).toBeInTheDocument();
    expect(screen.queryByText(/Verified catalog metadata/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Review suggested metadata" })).not.toBeInTheDocument();
  });

  it("applies working title without using verified catalog apply flow", async () => {
    putMock.mockResolvedValueOnce({ ...artwork, title: "Four Dancers" });
    const onApplied = vi.fn();

    render(
      <ResearchMetadataApply
        artwork={artwork}
        draft={legacyDraft}
        identification={null}
        canEdit
        onApplied={onApplied}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Use as working title" }));

    await waitFor(() => {
      expect(putMock).toHaveBeenCalledWith("/api/artworks/12", { title: "Four Dancers" });
      expect(onApplied).toHaveBeenCalled();
    });
  });
});
