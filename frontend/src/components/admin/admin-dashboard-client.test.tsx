"use client";

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AdminDashboardClient } from "@/components/admin/admin-dashboard-client";
import { AuthProvider } from "@/contexts/auth-context";

const postMock = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(async (path: string) => {
      if (path === "/api/auth/me") {
        return { email: "admin@example.com", name: "Admin", picture: null };
      }
      if (path === "/api/admin/summary") {
        return {
          visits: 2,
          artworks: 5,
          annotations: 3,
          cultural_entities: 1,
          research_notes: 0,
        };
      }
      if (path === "/api/admin/upload-health") {
        return {
          upload_dir: "/app/uploads",
          storage_backend: "filesystem",
          persistent: true,
          missing_count: 0,
          missing_record_count: 0,
          records: [],
        };
      }
      if (path.startsWith("/api/admin/visits")) {
        return {
          records: [
            {
              id: 1,
              museum_name: "National Gallery of Art",
              city: "Washington, DC",
              visit_date: "2026-05-25",
              notes: null,
              created_at: "2026-05-25T12:00:00Z",
            },
            {
              id: 2,
              museum_name: "Smithsonian American Art Museum",
              city: "Washington, DC",
              visit_date: "2026-05-24",
              notes: null,
              created_at: "2026-05-24T12:00:00Z",
            },
          ],
          meta: { total: 2, limit: 20, offset: 0, search: null },
        };
      }
      return { records: [], meta: { total: 0, limit: 20, offset: 0, search: null } };
    }),
    post: (...args: unknown[]) => postMock(...args),
    delete: vi.fn(),
  },
}));

vi.mock("@/lib/auth-storage", () => ({
  getAuthToken: () => "test-token",
  setAuthToken: vi.fn(),
}));

describe("AdminDashboardClient", () => {
  it("renders summary cards and visit table for signed-in admin", async () => {
    render(
      <AuthProvider googleConfigured={false}>
        <AdminDashboardClient />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getAllByText("National Gallery of Art").length).toBeGreaterThan(0);
    });

    expect(screen.getAllByText("Visits").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Artworks").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Upload storage" })).toBeInTheDocument();
    expect(screen.getByText("/app/uploads")).toBeInTheDocument();
  });

  it("supports bulk selection and delete confirmation", async () => {
    postMock.mockResolvedValueOnce({ deleted_count: 2 });

    render(
      <AuthProvider googleConfigured={false}>
        <AdminDashboardClient />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Select all visible" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Select all visible" }));
    expect(screen.getByText("2 selected")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Delete selected" }));
    expect(
      screen.getByText(
        "Delete 2 selected records? This cannot be undone. Deleting visits also removes their artworks, annotations, research notes, and cultural entities."
      )
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith("/api/admin/visits/bulk-delete", {
        ids: [1, 2],
      });
    });
  });
});
