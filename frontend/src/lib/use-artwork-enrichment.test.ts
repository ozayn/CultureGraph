import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ENRICHMENT_REQUEST_TIMEOUT_MS } from "@/lib/api";
import {
  ENRICHMENT_MAX_POLL_DURATION_MS,
  ENRICHMENT_POLL_INTERVAL_MS,
  isEnrichmentActive,
  resetArtworkEnrichmentStoreForTests,
  useArtworkEnrichment,
} from "@/lib/use-artwork-enrichment";
import { REQUEST_ABORT_MESSAGE } from "@/lib/request-errors";

const getMock = vi.fn();
const postMock = vi.fn();

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    api: {
      get: (...args: unknown[]) => getMock(...args),
      post: (...args: unknown[]) => postMock(...args),
    },
  };
});

function pendingState() {
  return {
    status: "pending" as const,
    stage: null,
    error: null,
    research_note_id: null,
    draft: null,
    lookup: null,
    identification: null,
    visual_analysis: null,
  };
}

function completedState() {
  return {
    status: "completed" as const,
    stage: null,
    error: null,
    research_note_id: 1,
    draft: {
      short_summary: "Done",
      historical_context: "Context",
      visual_elements_to_notice: [],
      related_questions: [],
      suggested_annotations: [],
      possible_title: null,
      possible_artist: null,
      period_or_movement: null,
    },
    lookup: null,
    identification: null,
    visual_analysis: null,
  };
}

async function flushPromises() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

describe("useArtworkEnrichment", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    getMock.mockReset();
    postMock.mockReset();
    resetArtworkEnrichmentStoreForTests();
    Object.defineProperty(document, "hidden", {
      configurable: true,
      value: false,
    });
  });

  afterEach(() => {
    resetArtworkEnrichmentStoreForTests();
    vi.useRealTimers();
  });

  it("loads enrichment once on subscribe", async () => {
    getMock.mockResolvedValueOnce(completedState());

    const { result } = renderHook(() => useArtworkEnrichment({ artworkId: 7 }));
    await flushPromises();

    expect(result.current.state?.status).toBe("completed");
    expect(getMock).toHaveBeenCalledTimes(1);
    expect(getMock).toHaveBeenCalledWith("/api/artworks/7/enrichment", {
      timeoutMs: ENRICHMENT_REQUEST_TIMEOUT_MS,
    });
  });

  it("polls only while enrichment is pending or running", async () => {
    getMock
      .mockResolvedValueOnce(pendingState())
      .mockResolvedValueOnce(pendingState())
      .mockResolvedValueOnce(completedState());

    const { result } = renderHook(() => useArtworkEnrichment({ artworkId: 7 }));
    await flushPromises();

    expect(result.current.state?.status).toBe("pending");
    expect(getMock).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(ENRICHMENT_POLL_INTERVAL_MS);
    });
    expect(getMock).toHaveBeenCalledTimes(2);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(ENRICHMENT_POLL_INTERVAL_MS);
    });
    expect(getMock).toHaveBeenCalledTimes(3);
    expect(result.current.state?.status).toBe("completed");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(ENRICHMENT_POLL_INTERVAL_MS * 3);
    });
    expect(getMock).toHaveBeenCalledTimes(3);
  });

  it("does not poll when disabled", async () => {
    getMock.mockResolvedValue(pendingState());

    renderHook(() => useArtworkEnrichment({ artworkId: 7, enabled: false }));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(ENRICHMENT_POLL_INTERVAL_MS * 3);
    });

    expect(getMock).not.toHaveBeenCalled();
  });

  it("deduplicates polling across multiple subscribers", async () => {
    getMock.mockResolvedValue(pendingState());

    renderHook(() => useArtworkEnrichment({ artworkId: 7 }));
    renderHook(() => useArtworkEnrichment({ artworkId: 7 }));
    await flushPromises();

    expect(getMock).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(ENRICHMENT_POLL_INTERVAL_MS);
    });

    expect(getMock).toHaveBeenCalledTimes(2);
  });

  it("stops polling after max duration", async () => {
    getMock.mockResolvedValue(pendingState());

    renderHook(() => useArtworkEnrichment({ artworkId: 7 }));
    await flushPromises();
    expect(getMock).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(ENRICHMENT_MAX_POLL_DURATION_MS + ENRICHMENT_POLL_INTERVAL_MS);
    });

    const callsAfterMax = getMock.mock.calls.length;

    await act(async () => {
      await vi.advanceTimersByTimeAsync(ENRICHMENT_POLL_INTERVAL_MS * 3);
    });

    expect(getMock.mock.calls.length).toBe(callsAfterMax);
  });

  it("does not poll while the document is hidden", async () => {
    getMock.mockResolvedValue(pendingState());

    renderHook(() => useArtworkEnrichment({ artworkId: 7 }));
    await flushPromises();
    expect(getMock).toHaveBeenCalledTimes(1);

    Object.defineProperty(document, "hidden", {
      configurable: true,
      value: true,
    });
    document.dispatchEvent(new Event("visibilitychange"));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(ENRICHMENT_POLL_INTERVAL_MS * 3);
    });

    expect(getMock).toHaveBeenCalledTimes(1);
  });

  it("uses long timeout for enrichment GET and POST", async () => {
    postMock.mockResolvedValueOnce(undefined);
    getMock.mockResolvedValueOnce(pendingState());

    const { result } = renderHook(() => useArtworkEnrichment({ artworkId: 7 }));
    await flushPromises();

    await act(async () => {
      await result.current.startEnrichment({ exactArtwork: true });
    });

    expect(postMock).toHaveBeenCalledWith(
      "/api/artworks/7/enrichment?exact_artwork=true",
      undefined,
      { timeoutMs: ENRICHMENT_REQUEST_TIMEOUT_MS }
    );
    expect(getMock).toHaveBeenCalledWith("/api/artworks/7/enrichment", {
      timeoutMs: ENRICHMENT_REQUEST_TIMEOUT_MS,
    });
  });

  it("deduplicates concurrent startEnrichment calls", async () => {
    let resolvePost: (() => void) | undefined;
    postMock.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolvePost = resolve;
        })
    );
    getMock.mockResolvedValue(pendingState());

    const { result } = renderHook(() => useArtworkEnrichment({ artworkId: 7 }));
    await flushPromises();

    let first: Promise<unknown> | undefined;
    let second: Promise<unknown> | undefined;
    await act(async () => {
      first = result.current.startEnrichment({ exactArtwork: true });
      second = result.current.startEnrichment({ exactArtwork: true });
    });

    expect(postMock).toHaveBeenCalledTimes(1);
    resolvePost?.();
    await act(async () => {
      await Promise.all([first, second]);
    });
  });

  it("maps abort errors to friendly enrichment copy", async () => {
    getMock.mockRejectedValueOnce(
      new DOMException("signal is aborted without reason", "AbortError")
    );

    const { result } = renderHook(() => useArtworkEnrichment({ artworkId: 7 }));
    await flushPromises();

    expect(result.current.error).toBe(REQUEST_ABORT_MESSAGE);
  });
});

describe("isEnrichmentActive", () => {
  it("returns true only for pending and running", () => {
    expect(isEnrichmentActive("pending")).toBe(true);
    expect(isEnrichmentActive("running")).toBe(true);
    expect(isEnrichmentActive("completed")).toBe(false);
    expect(isEnrichmentActive("failed")).toBe(false);
    expect(isEnrichmentActive("idle")).toBe(false);
  });
});
