const DEFAULT_API_BASE = "http://localhost:8000";

declare global {
  interface Window {
    __CULTUREGRAPH_API_URL__?: string;
  }
}

function normalizeApiBase(raw: string | undefined): string {
  const value = raw?.trim();
  if (!value) return DEFAULT_API_BASE;

  if (!/^https?:\/\//i.test(value)) {
    throw new Error(
      "NEXT_PUBLIC_API_URL must include http:// or https:// (e.g. https://your-api.up.railway.app)."
    );
  }

  return value.replace(/\/+$/, "");
}

function readRuntimeApiBaseFromDom(): string | null {
  if (typeof document === "undefined") return null;

  const fromBody = document.body?.dataset?.apiUrl?.trim();
  if (fromBody) return normalizeApiBase(fromBody);

  const fromWindow = window.__CULTUREGRAPH_API_URL__?.trim();
  if (fromWindow) return normalizeApiBase(fromWindow);

  return null;
}

/** Public API base URL for browser image/src and client fetch calls. */
export function getApiBase(): string {
  const runtime = readRuntimeApiBaseFromDom();
  if (runtime) return runtime;

  return normalizeApiBase(process.env.NEXT_PUBLIC_API_URL);
}

export function apiUrl(path: string): string {
  const base = getApiBase();
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}
