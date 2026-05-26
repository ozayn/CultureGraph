"use client";

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ArtworkImageLookupAction,
  ArtworkImageLookupPanel,
} from "@/components/artworks/artwork-image-lookup-panel";

const getMock = vi.fn();
const putMock = vi.fn();

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    api: {
      get: (...args: unknown[]) => getMock(...args),
      put: (...args: unknown[]) => putMock(...args),
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

const lookupResponse = {
  candidates: [
    {
      title: "The Adoration of the Magi",
      artist: "Botticelli",
      date: "1480",
      medium: "tempera",
      image_url: "https://example.com/image.jpg",
      image_thumbnail_url: "https://example.com/thumb.jpg",
      object_url: "https://example.com/object",
      accession_number: "123",
      source_name: "National Gallery of Art",
      confidence: 0.92,
      rights_label: "CC0",
      external_id: "nga-1",
      low_confidence: false,
    },
  ],
  sources_searched: ["National Gallery of Art"],
  query_used: "The Adoration of the Magi · Botticelli",
  query_source: "saved_title" as const,
  disclaimer: "Review before applying.",
};

describe("ArtworkImageLookupPanel", () => {
  afterEach(() => {
    cleanup();
    getMock.mockReset();
    putMock.mockReset();
  });

  it("shows Find official image for admin users", async () => {
    getMock.mockResolvedValueOnce({ ...lookupResponse, candidates: [] });

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

  it("shows query metadata and review step before saving", async () => {
    getMock.mockResolvedValueOnce(lookupResponse);
    putMock.mockResolvedValueOnce({ ...artwork, title: lookupResponse.candidates[0].title });

    render(
      <ArtworkImageLookupPanel artwork={artwork} canEdit hasImage={false} onApplied={vi.fn()}>
        <ArtworkImageLookupAction primary />
      </ArtworkImageLookupPanel>
    );

    fireEvent.click(screen.getByRole("button", { name: /Find official image/i }));

    await waitFor(() => {
      expect(screen.getByText(/Searching for:/)).toBeInTheDocument();
      expect(screen.getByText(/Saved title/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Use image + update title" }));

    expect(screen.getByText(/Review before saving/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Apply selected" }));

    await waitFor(() => {
      expect(putMock).toHaveBeenCalledWith(
        "/api/artworks/1",
        expect.objectContaining({
          image_url: "https://example.com/image.jpg",
          title: "The Adoration of the Magi",
        })
      );
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

  it("passes manual search overrides", async () => {
    getMock.mockResolvedValueOnce({
      ...lookupResponse,
      query_source: "manual",
      query_used: "Custom · Artist",
    });

    render(
      <ArtworkImageLookupPanel artwork={artwork} canEdit hasImage={false} onApplied={vi.fn()}>
        <ArtworkImageLookupAction primary />
      </ArtworkImageLookupPanel>
    );

    fireEvent.click(screen.getByRole("button", { name: /Find official image/i }));
    await waitFor(() => expect(getMock).toHaveBeenCalled());

    fireEvent.change(screen.getByLabelText("Search title"), {
      target: { value: "Custom" },
    });
    fireEvent.change(screen.getByLabelText("Search artist"), {
      target: { value: "Artist" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search again" }));

    await waitFor(() => {
      expect(getMock).toHaveBeenLastCalledWith(
        "/api/artworks/1/lookup-image?source=all&title_override=Custom&artist_override=Artist"
      );
    });
  });
});
