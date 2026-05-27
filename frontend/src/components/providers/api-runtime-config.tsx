"use client";

import { useEffect } from "react";

/** Copies server-injected API URL onto window for getApiBase() before hydration. */
export function ApiRuntimeConfig({ apiUrl }: { apiUrl: string }) {
  useEffect(() => {
    window.__CULTUREGRAPH_API_URL__ = apiUrl;
  }, [apiUrl]);

  return null;
}
