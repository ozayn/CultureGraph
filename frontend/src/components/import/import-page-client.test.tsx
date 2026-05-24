import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ImportPageClient } from "@/components/import/import-page-client";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

describe("ImportPageClient", () => {
  it("renders the paste step without crashing", () => {
    render(<ImportPageClient />);

    expect(
      screen.getByRole("heading", {
        name: /turn messy museum notes into your notebook/i,
      })
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/museum notes/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /extract entries/i })).toBeInTheDocument();
  });
});
