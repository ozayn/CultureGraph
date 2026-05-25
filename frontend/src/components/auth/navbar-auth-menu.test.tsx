"use client";

import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { NavbarAuthMenu } from "@/components/auth/navbar-auth-menu";
import { AuthProvider } from "@/contexts/auth-context";

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn().mockRejectedValue(new Error("unauthenticated")),
    post: vi.fn(),
  },
}));

describe("NavbarAuthMenu", () => {
  it("renders a native sign-in button without crashing", async () => {
    render(
      <AuthProvider googleConfigured={false}>
        <NavbarAuthMenu />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
    });
  });
});
