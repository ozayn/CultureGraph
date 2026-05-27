"use client";

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ArtworkDetailClient } from "@/components/artworks/artwork-detail-client";
import type { Artwork } from "@/lib/types";

vi.mock("@/components/auth/google-sign-in-button", () => ({
  GoogleSignInButton: () => <button type="button">Google sign-in</button>,
}));

vi.mock("@/contexts/auth-context", () => ({
  useAuth: () => ({
    canEdit: false,
    loading: false,
    user: null,
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
  ResearchPanel: () => (
    <div data-testid="research-panel">
      <button type="button" disabled>
        Research with AI
      </button>
      <p>Sign in to use AI research.</p>
    </div>
  ),
}));

vi.mock("@/components/artworks/photo-capture-date-suggestion", () => ({
  PhotoCaptureDateSuggestion: () => null,
}));

const artwork: Artwork = {
  id: 1,
  visit_id: 1,
  title: "Study",
  artist: "Artist",
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

describe("ArtworkDetailClient auth messaging", () => {
  afterEach(() => {
    cleanup();
  });

  it("shows one auth gate and no repeated edit CultureGraph headings", () => {
    render(<ArtworkDetailClient artwork={artwork} annotations={[]} />);

    expect(
      screen.getByText(
        /Anyone can browse\. Approved accounts can edit, annotate, upload, and run AI research\./
      )
    ).toBeInTheDocument();
    expect(screen.queryByText(/Sign in to edit CultureGraph/i)).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Google sign-in" })).toHaveLength(1);
  });
});
