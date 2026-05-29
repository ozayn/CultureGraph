import { getAuthToken } from "@/lib/auth-storage";
import { mapGoogleSignInError, parseApiErrorDetail } from "@/lib/auth-errors";
import { apiUrl } from "@/lib/api-config";
import { displayImageUrl, resolveImageUrl } from "@/lib/media-url";

export { apiUrl, getApiBase } from "@/lib/api-config";

const DEFAULT_REQUEST_TIMEOUT_MS = 25_000;
/** Museum-note import can call Claude and needs a longer client timeout than CRUD. */
export const IMPORT_REQUEST_TIMEOUT_MS = 120_000;
/** Photo uploads on mobile need more time after client-side normalization. */
export const UPLOAD_REQUEST_TIMEOUT_MS = 120_000;
/** Museum collection lookup can scan large indexes with semantic scoring. */
export const LOOKUP_REQUEST_TIMEOUT_MS = 90_000;
/** AI enrichment POST/GET polling — Claude vision + collection retrieval. */
export const ENRICHMENT_REQUEST_TIMEOUT_MS = 120_000;
/** Standalone research generation calls Claude synchronously. */
export const RESEARCH_REQUEST_TIMEOUT_MS = 120_000;

export function mediaUrl(path: string | null | undefined): string | null {
  return resolveImageUrl(path);
}

/** Local blob/data URLs and remote paths suitable for `<img src>`. */
export function resolveArtworkImageSrc(url: string): string {
  return displayImageUrl(url) ?? url;
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
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    if (error instanceof TypeError) {
      throw error;
    }
    throw error;
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
  get: <T>(path: string, options?: Pick<ApiRequestOptions, "timeoutMs">) =>
    request<T>(path, { timeoutMs: options?.timeoutMs }),
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
  delete: <T = void>(path: string) => request<T>(path, { method: "DELETE" }),
  upload: <T>(
    path: string,
    file: File,
    fields?: Record<string, string | null | undefined>
  ) => {
    const form = new FormData();
    form.append("file", file);
    if (fields) {
      for (const [key, value] of Object.entries(fields)) {
        if (value != null && value !== "") {
          form.append(key, value);
        }
      }
    }
    return request<T>(path, {
      method: "POST",
      body: form,
      timeoutMs: UPLOAD_REQUEST_TIMEOUT_MS,
    });
  },
};
