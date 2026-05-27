"use client";

import { useEffect } from "react";

/** Mirrors server-injected API URL on window for callers that read it directly. */
export function ApiRuntimeConfig({ apiUrl }: { apiUrl: string }) {
  useEffect(() => {
    window.__CULTUREGRAPH_API_URL__ = apiUrl;
  }, [apiUrl]);

  return null;
}
