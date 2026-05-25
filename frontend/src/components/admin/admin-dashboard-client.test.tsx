"use client";

import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AdminDashboardClient } from "@/components/admin/admin-dashboard-client";
import { AuthProvider } from "@/contexts/auth-context";

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
          ],
          meta: { total: 1, limit: 20, offset: 0, search: null },
        };
      }
      return { records: [], meta: { total: 0, limit: 20, offset: 0, search: null } };
    }),
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
  });
});
