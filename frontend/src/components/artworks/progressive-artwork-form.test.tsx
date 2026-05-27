import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ProgressiveArtworkForm } from "@/components/artworks/progressive-artwork-form";

const postMock = vi.fn();
const uploadMock = vi.fn();
const pushMock = vi.fn();
const prepareMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, refresh: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  api: {
    post: (...args: unknown[]) => postMock(...args),
    put: vi.fn(),
    upload: (...args: unknown[]) => uploadMock(...args),
  },
}));

vi.mock("@/lib/prepare-artwork-upload", () => ({
  prepareArtworkUploadFile: (...args: unknown[]) => prepareMock(...args),
}));

describe("ProgressiveArtworkForm", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:preview"),
      revokeObjectURL: vi.fn(),
    });
    postMock.mockReset();
    uploadMock.mockReset();
    pushMock.mockReset();
    prepareMock.mockReset();
    prepareMock.mockImplementation(async (file: File) => ({
      file,
      wasNormalized: false,
      originalSize: file.size,
      outputSize: file.size,
      capturedAt: "2026-05-23T14:30:00Z",
    }));
  });

  it("opens artwork detail with enrichment after draft save", async () => {
    postMock.mockResolvedValueOnce({ id: 42, title: null, captured_date_source: "none" });
    uploadMock.mockResolvedValueOnce({
      id: 42,
      title: null,
      captured_date_source: "none",
    });

    render(<ProgressiveArtworkForm visitId={1} />);

    const file = new File(["pixels"], "photo.png", { type: "image/png" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByTestId("save-draft"));

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
      expect(prepareMock).toHaveBeenCalled();
      expect(uploadMock).toHaveBeenCalled();
      expect(pushMock).toHaveBeenCalledWith("/artworks/42?enrich=1");
    });
  });

  it("can still return to visit when configured", async () => {
    postMock.mockResolvedValueOnce({ id: 42, title: null, captured_date_source: "none" });
    uploadMock.mockResolvedValueOnce({
      id: 42,
      title: null,
      captured_date_source: "none",
    });

    render(<ProgressiveArtworkForm visitId={1} returnToVisitAfterDraft />);

    const file = new File(["pixels"], "photo.png", { type: "image/png" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByTestId("save-draft"));

    await waitFor(() => {
      expect(pushMock).toHaveBeenCalledWith("/visits/1");
    });
  });

  it("shows friendly message instead of raw Failed to fetch", async () => {
    postMock.mockResolvedValueOnce({ id: 42, title: null, captured_date_source: "none" });
    uploadMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    render(<ProgressiveArtworkForm visitId={1} redirectOnSave={false} openEnrichmentAfterSave={false} />);

    const file = new File(["pixels"], "photo.png", { type: "image/png" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByTestId("save-draft"));

    await waitFor(() => {
      expect(screen.getByText("Connection issue — try again.")).toBeInTheDocument();
      expect(screen.queryByText("Failed to fetch")).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
    });
  });
});
