"use client";

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ArtworkImageLookupAction,
  ArtworkImageLookupPanel,
} from "@/components/artworks/artwork-image-lookup-panel";

const getMock = vi.fn();

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    api: {
      get: (...args: unknown[]) => getMock(...args),
      put: vi.fn(),
    },
  };
});

const artwork = {
  id: 1,
  visit_id: 1,
  title: "The Adoration of the Magi",
  artist: "Botticelli",
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

describe("ArtworkImageLookupPanel", () => {
  afterEach(() => {
    cleanup();
  });

  it("shows Find official image for admin users", async () => {
    getMock.mockResolvedValueOnce({
      candidates: [],
      sources_searched: ["National Gallery of Art"],
    });

    render(
      <ArtworkImageLookupPanel artwork={artwork} canEdit hasImage={false} onApplied={vi.fn()}>
        <ArtworkImageLookupAction primary />
      </ArtworkImageLookupPanel>
    );

    expect(screen.getByTestId("artwork-official-image-lookup-primary")).toHaveTextContent(
      "Find official image"
    );

    fireEvent.click(screen.getByRole("button", { name: /Find official image/i }));

    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith("/api/artworks/1/lookup-image?source=all");
    });
  });

  it("shows Replace official image when artwork has a photo", () => {
    render(
      <ArtworkImageLookupPanel
        artwork={{ ...artwork, image_url: "/uploads/1.jpg" }}
        canEdit
        hasImage
        onApplied={vi.fn()}
      >
        <ArtworkImageLookupAction variant="replace" />
      </ArtworkImageLookupPanel>
    );

    expect(screen.getByRole("button", { name: "Replace official image" })).toBeInTheDocument();
  });

  it("hides the action for non-admin users", () => {
    render(
      <ArtworkImageLookupPanel artwork={artwork} canEdit={false} hasImage={false} onApplied={vi.fn()}>
        <ArtworkImageLookupAction />
      </ArtworkImageLookupPanel>
    );

    expect(screen.queryByTestId("artwork-official-image-lookup-primary")).not.toBeInTheDocument();
  });

  it("shows metadata hint when title and artist are missing", async () => {
    getMock.mockResolvedValueOnce({ candidates: [], sources_searched: [] });

    render(
      <ArtworkImageLookupPanel
        artwork={{ ...artwork, title: "", artist: null }}
        canEdit
        hasImage={false}
        onApplied={vi.fn()}
      >
        <ArtworkImageLookupAction primary />
      </ArtworkImageLookupPanel>
    );

    fireEvent.click(screen.getByRole("button", { name: /Find official image/i }));

    await waitFor(() => {
      expect(
        screen.getByText("Add a title or artist to improve search results.")
      ).toBeInTheDocument();
    });
  });
});
