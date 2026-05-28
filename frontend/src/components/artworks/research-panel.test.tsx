"use client";

import type { ReactNode } from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ArtworkImageLookupPanel,
} from "@/components/artworks/artwork-image-lookup-panel";
import { ResearchPanel } from "@/components/artworks/research-panel";

const getMock = vi.fn();
const putMock = vi.fn();
const postMock = vi.fn();

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    api: {
      get: (...args: unknown[]) => getMock(...args),
      put: (...args: unknown[]) => putMock(...args),
      post: (...args: unknown[]) => postMock(...args),
      delete: vi.fn(),
    },
  };
});

vi.mock("@/components/artworks/ai-suggested-annotations", () => ({
  AiSuggestedAnnotations: () => null,
}));

vi.mock("@/components/auth/sign-in-prompt", () => ({
  SignInPrompt: () => null,
}));

const artwork = {
  id: 1,
  visit_id: 1,
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
  captured_date_source: "none" as const,
  catalog_source: null,
  catalog_object_url: null,
  catalog_accession_number: null,
  catalog_rights_label: null,
  personal_notes: null,
  created_at: "2026-05-25T12:00:00Z",
};

const researchNote = {
  id: 10,
  artwork_id: 1,
  short_summary: "Four Dancers — possibly by Edgar Degas",
  historical_context: "A rehearsal scene from Degas's ballet series.",
  visual_elements_to_notice: "[]",
  related_questions: "[]",
  suggested_annotations: JSON.stringify([
    {
      category: "material",
      note: "Pastel on paper",
      tags: [],
      linked_concept_names: [],
      confidence: 0.8,
      suggested_position: { x_percent: null, y_percent: null, reason: null },
    },
  ]),
  possible_title: "Four Dancers — possibly by Edgar Degas",
  possible_artist: "Edgar Degas",
  period_or_movement: "Impressionism, c. 1890",
  created_at: "2026-05-25T12:00:00Z",
};

function renderWithLookup(ui: ReactNode) {
  return render(
    <ArtworkImageLookupPanel artwork={artwork} canEdit hasImage={false} onApplied={vi.fn()}>
      {ui}
    </ArtworkImageLookupPanel>
  );
}

describe("ResearchPanel metadata apply", () => {
  afterEach(() => {
    cleanup();
    getMock.mockReset();
    putMock.mockReset();
    postMock.mockReset();
  });

  it("shows a single Review suggested metadata action", async () => {
    getMock.mockResolvedValueOnce([researchNote]);

    renderWithLookup(
      <ResearchPanel artwork={artwork} canEdit onArtworkUpdated={vi.fn()} />
    );

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: "Review suggested metadata" })
      ).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: "Use title" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Use this title" })).not.toBeInTheDocument();
  });

  it("updates selected artwork fields after review confirm", async () => {
    getMock.mockResolvedValueOnce([researchNote]);
    putMock.mockResolvedValueOnce({
      ...artwork,
      year_period: "c. 1890 · Impressionism",
      medium: "Pastel on paper",
    });
    const onArtworkUpdated = vi.fn();

    renderWithLookup(
      <ResearchPanel artwork={artwork} canEdit onArtworkUpdated={onArtworkUpdated} />
    );

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: "Review suggested metadata" })
      ).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Review suggested metadata" }));
    expect(screen.getByText(/Review before saving/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("checkbox", { name: /Year \/ date/i }));
    fireEvent.click(screen.getByRole("checkbox", { name: /Period \/ movement/i }));
    fireEvent.click(screen.getByRole("checkbox", { name: /Medium/i }));

    fireEvent.click(screen.getByRole("button", { name: "Apply selected" }));

    await waitFor(() => {
      expect(putMock).toHaveBeenCalledWith(
        "/api/artworks/1",
        expect.objectContaining({
          year_period: "c. 1890 · Impressionism",
          medium: "Pastel on paper",
        })
      );
      expect(putMock.mock.calls[0]?.[1]).not.toHaveProperty("title");
      expect(putMock.mock.calls[0]?.[1]).not.toHaveProperty("artist");
      expect(onArtworkUpdated).toHaveBeenCalled();
    });

    expect(screen.getByText(/Artwork metadata updated/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Find official image" })).toBeInTheDocument();
  });

  it("hides apply actions for non-admin users", async () => {
    getMock.mockResolvedValueOnce([researchNote]);

    renderWithLookup(<ResearchPanel artwork={artwork} canEdit={false} />);

    await waitFor(() => {
      expect(screen.getByText("Summary")).toBeInTheDocument();
    });

    expect(
      screen.queryByRole("button", { name: "Review suggested metadata" })
    ).not.toBeInTheDocument();
  });
});
