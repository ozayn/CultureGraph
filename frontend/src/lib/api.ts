import { getAuthToken } from "@/lib/auth-storage";
import { mapGoogleSignInError, parseApiErrorDetail } from "@/lib/auth-errors";

const DEFAULT_API_BASE = "http://localhost:8000";
const DEFAULT_REQUEST_TIMEOUT_MS = 20_000;
/** Museum-note import can call Claude and needs a longer client timeout than CRUD. */
export const IMPORT_REQUEST_TIMEOUT_MS = 120_000;

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

export function mediaUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (path.startsWith("http")) return path;
  return apiUrl(path);
}

type ApiRequestOptions = Omit<RequestInit, "signal"> & {
  timeoutMs?: number;
};

async function request<T>(
  path: string,
  options: ApiRequestOptions = {}
): Promise<T> {
  const { timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS, ...fetchOptions } = options;
  const token = getAuthToken();
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      ...fetchOptions,
      signal: controller.signal,
      headers: {
        ...(fetchOptions.body instanceof FormData
          ? {}
          : { "Content-Type": "application/json" }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...fetchOptions.headers,
      },
      cache: "no-store",
    });
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    const detail = await response.text();
    const trimmed = detail.trimStart();
    if (trimmed.startsWith("<!DOCTYPE") || trimmed.startsWith("<html")) {
      throw new Error(
        `API returned HTML (status ${response.status}). Check NEXT_PUBLIC_API_URL — it must point to the CultureGraph API service, not the web app.`
      );
    }

    const parsedDetail = parseApiErrorDetail(detail);
    if (path === "/api/auth/google") {
      throw new Error(mapGoogleSignInError(response.status, parsedDetail));
    }

    throw new Error(parsedDetail || `Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(
    path: string,
    body?: unknown,
    options?: Pick<ApiRequestOptions, "timeoutMs">
  ) =>
    request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
      timeoutMs: options?.timeoutMs,
    }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: (path: string) => request<void>(path, { method: "DELETE" }),
  upload: <T>(path: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<T>(path, { method: "POST", body: form });
  },
};
