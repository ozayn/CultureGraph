"use client";

import { useCallback, useRef, useState } from "react";

import { api, LENS_SEARCH_REQUEST_TIMEOUT_MS } from "@/lib/api";
import { mapRequestError } from "@/lib/request-errors";
import type { LensSearchResponse } from "@/lib/types";

export function useArtworkLensSearch(artworkId: number) {
  const [result, setResult] = useState<LensSearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inFlightRef = useRef<Promise<LensSearchResponse | null> | null>(null);

  const runLensSearch = useCallback(async () => {
    if (inFlightRef.current) {
      return inFlightRef.current;
    }

    inFlightRef.current = (async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await api.post<LensSearchResponse>(
          `/api/artworks/${artworkId}/lens-search`,
          undefined,
          { timeoutMs: LENS_SEARCH_REQUEST_TIMEOUT_MS }
        );
        setResult(response);
        return response;
      } catch (err) {
        const message = mapRequestError(err, "Web visual search failed.");
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

  const resetLensSearch = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return {
    result,
    loading,
    error,
    runLensSearch,
    resetLensSearch,
  };
}
