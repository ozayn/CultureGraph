"use client";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { VisitDetailClient } from "@/components/visits/visit-detail-client";
import { AuthProvider } from "@/contexts/auth-context";
import { getAuthToken } from "@/lib/auth-storage";

const deleteMock = vi.fn();
const refreshMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    refresh: refreshMock,
  }),
}));

vi.mock("@/lib/auth-storage", () => ({
  getAuthToken: vi.fn(() => "test-token"),
  setAuthToken: vi.fn(),
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    api: {
      get: vi.fn(async (path: string) => {
        if (path === "/api/auth/me") {
          return { email: "admin@example.com", name: "Admin", picture: null };
        }
        return null;
      }),
      delete: (...args: unknown[]) => deleteMock(...args),
    },
  };
});

const visit = {
  id: 1,
  museum_name: "National Gallery of Art",
  city: "Washington, DC",
  visit_date: "2026-05-23",
  notes: null,
  created_at: "2026-05-25T12:00:00Z",
};

const artworks = [
  {
    id: 10,
    visit_id: 1,
    title: "Sunflowers",
    artist: "Van Gogh",
    year_period: "1888",
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
  },
  {
    id: 11,
    visit_id: 1,
    title: "Water Lilies",
    artist: "Monet",
    year_period: "1919",
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
  },
];

describe("VisitDetailClient artwork delete", () => {
  it("renders visit calendar date without timezone shift", async () => {
    render(
      <AuthProvider googleConfigured={false}>
        <VisitDetailClient visit={visit} artworks={artworks} culturalEntities={[]} />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/May 23, 2026/)).toBeInTheDocument();
    });
  });

  it("shows delete control for signed-in admin and removes artwork after confirm", async () => {
    deleteMock.mockResolvedValueOnce(undefined);

    render(
      <AuthProvider googleConfigured={false}>
        <VisitDetailClient visit={visit} artworks={artworks} culturalEntities={[]} />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Sunflowers")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Actions for Sunflowers" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "Delete" }));

    expect(
      screen.getByText(
        "Delete this artwork? Its annotations and research notes may also be removed."
      )
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(deleteMock).toHaveBeenCalledWith("/api/artworks/10");
    });

    await waitFor(() => {
      expect(screen.queryByText("Sunflowers")).not.toBeInTheDocument();
      expect(screen.getByText("Water Lilies")).toBeInTheDocument();
    });

    expect(refreshMock).toHaveBeenCalled();
  });

  it("hides delete controls for logged-out users", async () => {
    vi.mocked(getAuthToken).mockReturnValueOnce(null);

    render(
      <AuthProvider googleConfigured={false}>
        <VisitDetailClient visit={visit} artworks={artworks} culturalEntities={[]} />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("Sunflowers")).toBeInTheDocument();
    });

    expect(screen.queryByRole("button", { name: "Actions for Sunflowers" })).not.toBeInTheDocument();
  });
});
