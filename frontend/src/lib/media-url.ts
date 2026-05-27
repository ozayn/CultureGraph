import { apiUrl, getApiBase } from "@/lib/api-config";

const MUSEUM_IMAGE_HOST_SUFFIXES = [
  "nga.gov",
  "si.edu",
  "smithsonian.edu",
  "americanart.si.edu",
] as const;

function encodeMediaUrl(url: string): string {
  try {
    return new URL(url).href;
  } catch {
    return encodeURI(url);
  }
}

/** Upgrade http→https when the page is served over https (avoids mixed-content blocks on mobile). */
function coerceBrowserSafeUrl(url: string): string {
  if (typeof window === "undefined") return url;
  if (window.location.protocol === "https:" && url.startsWith("http://")) {
    return `https://${url.slice("http://".length)}`;
  }
  return url;
}

/**
 * Resolve artwork/entity image paths to a browser-loadable absolute URL.
 * - `/uploads/...` → prefixed with the public API base URL
 * - `https://...` museum URLs → used as-is (optionally proxied for display)
 */
export function resolveImageUrl(path: string | null | undefined): string | null {
  if (!path?.trim()) return null;

  const trimmed = path.trim();
  if (trimmed.startsWith("blob:") || trimmed.startsWith("data:")) {
    return trimmed;
  }

  if (trimmed.startsWith("//")) {
    return coerceBrowserSafeUrl(encodeMediaUrl(`https:${trimmed}`));
  }

  if (/^https?:\/\//i.test(trimmed)) {
    return coerceBrowserSafeUrl(encodeMediaUrl(trimmed));
  }

  const normalizedPath = trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
  if (normalizedPath.startsWith("/uploads/")) {
    return coerceBrowserSafeUrl(encodeMediaUrl(apiUrl(normalizedPath)));
  }

  return coerceBrowserSafeUrl(encodeMediaUrl(apiUrl(normalizedPath)));
}

/** @deprecated Use resolveImageUrl */
export const resolveMediaUrl = resolveImageUrl;

function isMuseumImageHost(hostname: string): boolean {
  const host = hostname.toLowerCase();
  return MUSEUM_IMAGE_HOST_SUFFIXES.some(
    (suffix) => host === suffix || host.endsWith(`.${suffix}`)
  );
}

function isSameApiHost(url: string): boolean {
  try {
    const imageOrigin = new URL(url).origin;
    const apiOrigin = new URL(getApiBase()).origin;
    return imageOrigin === apiOrigin;
  } catch {
    return false;
  }
}

export function shouldProxyExternalImage(url: string): boolean {
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:") return false;
    if (isSameApiHost(url)) return false;
    return isMuseumImageHost(parsed.hostname);
  } catch {
    return false;
  }
}

function withMuseumProxy(resolved: string): string {
  if (shouldProxyExternalImage(resolved)) {
    return `${getApiBase()}/api/image-proxy?url=${encodeURIComponent(resolved)}`;
  }
  return resolved;
}

/** Card thumbnails — thumbnail_url preferred by caller. */
export function thumbnailDisplayUrl(path: string | null | undefined): string | null {
  const resolved = resolveImageUrl(path);
  if (!resolved) return null;
  return withMuseumProxy(resolved);
}

/** Detail hero and full-size artwork display. */
export function displayImageUrl(path: string | null | undefined): string | null {
  const resolved = resolveImageUrl(path);
  if (!resolved) return null;
  return withMuseumProxy(resolved);
}
