const DEFAULT_API_BASE = "http://localhost:8000";

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

const API_BASE = normalizeApiBase(process.env.NEXT_PUBLIC_API_URL);

export function getApiBase(): string {
  return API_BASE;
}

export function apiUrl(path: string): string {
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}
