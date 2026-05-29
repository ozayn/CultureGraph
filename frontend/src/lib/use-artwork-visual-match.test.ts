"use client";

import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { VISUAL_MATCH_REQUEST_TIMEOUT_MS } from "@/lib/api";
import { useArtworkVisualMatch } from "@/lib/use-artwork-visual-match";

const postMock = vi.fn();

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      post: (...args: unknown[]) => postMock(...args),
    },
  };
});

describe("useArtworkVisualMatch", () => {
  beforeEach(() => {
    postMock.mockReset();
  });

  it("uses long timeout for visual match requests", async () => {
    postMock.mockResolvedValueOnce({ candidates: [], index_status: "empty" });

    const { result } = renderHook(() => useArtworkVisualMatch(9));
    await act(async () => {
      await result.current.runVisualMatch();
    });

    expect(postMock).toHaveBeenCalledWith(
      "/api/artworks/9/visual-match",
      undefined,
      { timeoutMs: VISUAL_MATCH_REQUEST_TIMEOUT_MS }
    );
  });

  it("deduplicates concurrent visual match requests", async () => {
    let resolvePost: (() => void) | undefined;
    postMock.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolvePost = () => resolve({ candidates: [], index_status: "ready" });
        })
    );

    const { result } = renderHook(() => useArtworkVisualMatch(9));
    let first: Promise<unknown> | undefined;
    let second: Promise<unknown> | undefined;
    await act(async () => {
      first = result.current.runVisualMatch();
      second = result.current.runVisualMatch();
    });

    expect(postMock).toHaveBeenCalledTimes(1);
    resolvePost?.();
    await act(async () => {
      await Promise.all([first, second]);
    });
  });
});
