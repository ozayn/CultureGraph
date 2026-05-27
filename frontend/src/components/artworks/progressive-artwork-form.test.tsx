import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProgressiveArtworkForm } from "@/components/artworks/progressive-artwork-form";

const postMock = vi.fn();
const uploadMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  api: {
    post: (...args: unknown[]) => postMock(...args),
    put: vi.fn(),
    upload: (...args: unknown[]) => uploadMock(...args),
  },
}));

describe("ProgressiveArtworkForm", () => {
  beforeEach(() => {
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:preview"),
      revokeObjectURL: vi.fn(),
    });
    postMock.mockReset();
    uploadMock.mockReset();
  });

  it("creates untitled artwork when saving with photo only", async () => {
    postMock.mockResolvedValueOnce({ id: 42, title: null, captured_date_source: "none" });

    render(<ProgressiveArtworkForm visitId={1} redirectOnSave={false} />);

    const file = new File(["pixels"], "photo.png", { type: "image/png" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByRole("button", { name: "Save now" }));

    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith("/api/artworks", {
        title: null,
        artist: null,
        year_period: null,
        medium: null,
        museum_gallery: null,
        personal_notes: null,
        visit_id: 1,
      });
    });
  });
});
