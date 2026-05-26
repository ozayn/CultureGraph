"use client";

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

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
  historical_context: "Context",
  visual_elements_to_notice: "[]",
  related_questions: "[]",
  suggested_annotations: "[]",
  possible_title: "Four Dancers — possibly by Edgar Degas",
  possible_artist: "Edgar Degas",
  period_or_movement: "Impressionism",
  created_at: "2026-05-25T12:00:00Z",
};

describe("ResearchPanel metadata apply", () => {
  afterEach(() => {
    cleanup();
    getMock.mockReset();
    putMock.mockReset();
    postMock.mockReset();
  });

  it("renders Use this title for admin users when AI title exists", async () => {
    getMock.mockResolvedValueOnce([researchNote]);

    render(
      <ResearchPanel artwork={artwork} canEdit onArtworkUpdated={vi.fn()} />
    );

    await waitFor(() => {
      expect(screen.getByText(/AI suggested title:/)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Use this title" })).toBeInTheDocument();
    });
  });

  it("updates artwork title after review confirm", async () => {
    getMock.mockResolvedValueOnce([researchNote]);
    putMock.mockResolvedValueOnce({ ...artwork, title: "Four Dancers", artist: "Edgar Degas" });
    const onArtworkUpdated = vi.fn();

    render(
      <ResearchPanel artwork={artwork} canEdit onArtworkUpdated={onArtworkUpdated} />
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Use this title" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Use this title" }));
    expect(screen.getByText(/Review before saving/)).toBeInTheDocument();
    expect(screen.getAllByText("Unknown").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Apply selected" }));

    await waitFor(() => {
      expect(putMock).toHaveBeenCalledWith("/api/artworks/1", { title: "Four Dancers" });
      expect(onArtworkUpdated).toHaveBeenCalledWith(
        expect.objectContaining({ title: "Four Dancers" })
      );
    });
  });

  it("hides apply actions for non-admin users", async () => {
    getMock.mockResolvedValueOnce([researchNote]);

    render(<ResearchPanel artwork={artwork} canEdit={false} />);

    await waitFor(() => {
      expect(screen.getByText("Summary")).toBeInTheDocument();
    });

    expect(screen.queryByRole("button", { name: "Use this title" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Use title" })).not.toBeInTheDocument();
  });
});
