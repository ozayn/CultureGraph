"use client";

import { useCallback, useRef, useState } from "react";

import { api, VISUAL_MATCH_REQUEST_TIMEOUT_MS } from "@/lib/api";
import { mapRequestError } from "@/lib/request-errors";
import type { VisualMatchResponse } from "@/lib/types";

export function useArtworkVisualMatch(artworkId: number) {
  const [result, setResult] = useState<VisualMatchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inFlightRef = useRef<Promise<VisualMatchResponse | null> | null>(null);

  const runVisualMatch = useCallback(async () => {
    if (inFlightRef.current) {
      return inFlightRef.current;
    }

    inFlightRef.current = (async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await api.post<VisualMatchResponse>(
          `/api/artworks/${artworkId}/visual-match`,
          undefined,
          { timeoutMs: VISUAL_MATCH_REQUEST_TIMEOUT_MS }
        );
        setResult(response);
        return response;
      } catch (err) {
        const message = mapRequestError(err, "Visual matching failed.");
        setError(message);
        setResult(null);
        return null;
      } finally {
        setLoading(false);
        inFlightRef.current = null;
      }
    })();

    return inFlightRef.current;
  }, [artworkId]);

  const resetVisualMatch = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return {
    result,
    loading,
    error,
    runVisualMatch,
    resetVisualMatch,
  };
}
