"use client";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  ArtworkImageLookupPanel,
  ArtworkImageLookupProvider,
  ArtworkImageLookupTrigger,
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

describe("ArtworkImageLookupPanel", () => {
  it("shows Find official image and opens lookup sheet", async () => {
    getMock.mockResolvedValueOnce({
      candidates: [
        {
          title: "The Adoration of the Magi",
          artist: "Botticelli",
          date: "1475",
          medium: "Tempera",
          image_url: "https://example.com/image.jpg",
          image_thumbnail_url: "https://example.com/thumb.jpg",
          object_url: "https://example.com/record",
          accession_number: "1943.3.1",
          source_name: "National Gallery of Art",
          confidence: 0.9,
          rights_label: "CC0",
          external_id: "123",
        },
      ],
      sources_searched: ["National Gallery of Art"],
      disclaimer: "Review before applying.",
    });

    render(
      <ArtworkImageLookupPanel
        artwork={artwork}
        canEdit
        onApplied={vi.fn()}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /Find official image/i }));

    await waitFor(() => {
      expect(getMock).toHaveBeenCalledWith("/api/artworks/1/lookup-image?source=all");
    });

    await waitFor(() => {
      expect(screen.getByText("The Adoration of the Magi")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Use this image" })).toBeInTheDocument();
    });
  });

  it("shows Replace image variant when artwork has a photo", () => {
    render(
      <ArtworkImageLookupProvider
        artwork={{ ...artwork, image_url: "/uploads/1.jpg" }}
        canEdit
        hasImage
        onApplied={vi.fn()}
      >
        <ArtworkImageLookupTrigger variant="replace" />
      </ArtworkImageLookupProvider>
    );

    expect(screen.getByRole("button", { name: "Replace image" })).toBeInTheDocument();
  });
});
