import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PhotoCaptureDateSuggestion } from "@/components/artworks/photo-capture-date-suggestion";

const getMock = vi.fn();
const patchMock = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    get: (...args: unknown[]) => getMock(...args),
    patch: (...args: unknown[]) => patchMock(...args),
  },
}));

const artwork = {
  id: 1,
  visit_id: 9,
  captured_at: "2026-05-23T14:30:00Z",
  captured_date_source: "exif" as const,
};

describe("PhotoCaptureDateSuggestion", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    getMock.mockReset();
    patchMock.mockReset();
    getMock.mockResolvedValue({ id: 9, visit_date: "2026-05-25" });
  });

  it("shows when photo date differs from visit date", async () => {
    render(<PhotoCaptureDateSuggestion artwork={artwork} />);

    expect(
      await screen.findByText(/This photo appears to have been taken on/i)
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Use photo date" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Not now" })).toBeInTheDocument();
  });

  it("hides when visit date already matches photo date", () => {
    render(
      <PhotoCaptureDateSuggestion artwork={artwork} visitDate="2026-05-23" />
    );

    expect(
      screen.queryByText(/This photo appears to have been taken on/i)
    ).not.toBeInTheDocument();
  });

  it("updates visit date when confirmed", async () => {
    patchMock.mockResolvedValueOnce({ id: 9, visit_date: "2026-05-23" });
    const onVisitUpdated = vi.fn();

    render(
      <PhotoCaptureDateSuggestion
        artwork={artwork}
        visitDate="2026-05-25"
        onVisitUpdated={onVisitUpdated}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Use photo date" }));

    await waitFor(() => {
      expect(patchMock).toHaveBeenCalledWith("/api/visits/9", {
        visit_date: "2026-05-23",
      });
      expect(onVisitUpdated).toHaveBeenCalled();
    });
  });

  it("dismisses when Not now is clicked", () => {
    render(
      <PhotoCaptureDateSuggestion artwork={artwork} visitDate="2026-05-25" />
    );

    fireEvent.click(screen.getByRole("button", { name: "Not now" }));

    expect(
      screen.queryByText(/This photo appears to have been taken on/i)
    ).not.toBeInTheDocument();
  });

  it("shows nothing without EXIF capture metadata", () => {
    render(
      <PhotoCaptureDateSuggestion
        artwork={{
          ...artwork,
          captured_at: null,
          captured_date_source: "none",
        }}
      />
    );

    expect(
      screen.queryByText(/This photo appears to have been taken on/i)
    ).not.toBeInTheDocument();
  });
});
