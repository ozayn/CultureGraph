"use client";

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ArtworkDetailClient } from "@/components/artworks/artwork-detail-client";
import type { Artwork } from "@/lib/types";

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => ({
    canEdit: true,
    loading: false,
    user: { email: "admin@test.com" },
    googleConfigured: true,
    signInLoading: false,
    signInError: null,
    signInWithGoogleToken: vi.fn(),
    clearSignInError: vi.fn(),
    signOut: vi.fn(),
    refreshUser: vi.fn(),
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("@/components/artworks/research-panel", () => ({
  ResearchPanel: () => <div data-testid="research-panel" />,
}));

vi.mock("@/components/artworks/photo-capture-date-suggestion", () => ({
  PhotoCaptureDateSuggestion: () => null,
}));

const artworkWithImage: Artwork = {
  id: 173,
  visit_id: 158,
  title: "painting",
  artist: null,
  year_period: null,
  medium: null,
  museum_gallery: null,
  image_url: "/uploads/artworks/173/display.webp",
  image_thumbnail_url: "/uploads/artworks/173/thumb.webp",
  image_width: 1600,
  image_height: 1067,
  image_mime_type: "image/webp",
  image_file_size: 164046,
  captured_at: null,
  captured_date_source: "none",
  catalog_source: null,
  catalog_object_url: null,
  catalog_accession_number: null,
  catalog_rights_label: null,
  personal_notes: null,
  created_at: "2026-05-25T12:00:00Z",
};

describe("ArtworkDetailClient official image lookup", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders Replace official image for admin when artwork has an image", () => {
    render(
      <ArtworkDetailClient
        artwork={artworkWithImage}
        annotations={[]}
      />
    );

    expect(screen.getByTestId("artwork-official-image-lookup-primary")).toHaveTextContent(
      "Replace official image"
    );
  });

  it("renders Find official image for admin when artwork has no image", () => {
    render(
      <ArtworkDetailClient
        artwork={{ ...artworkWithImage, image_url: null, image_thumbnail_url: null }}
        annotations={[]}
      />
    );

    expect(screen.getByTestId("artwork-official-image-lookup-primary")).toHaveTextContent(
      "Find official image"
    );
  });
});
