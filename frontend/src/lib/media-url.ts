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

/** Resolve artwork/entity image paths to a browser-loadable absolute URL. */
export function resolveMediaUrl(path: string | null | undefined): string | null {
  if (!path?.trim()) return null;

  const trimmed = path.trim();
  if (trimmed.startsWith("blob:") || trimmed.startsWith("data:")) {
    return trimmed;
  }

  if (trimmed.startsWith("//")) {
    return encodeMediaUrl(`https:${trimmed}`);
  }

  if (/^https?:\/\//i.test(trimmed)) {
    return encodeMediaUrl(trimmed);
  }

  const normalizedPath = trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
  return encodeMediaUrl(apiUrl(normalizedPath));
}

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

/** Use API proxy for external museum thumbnails that may block hotlinking. */
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

/** Thumbnail/card image src — resolves relative uploads and proxies museum URLs when needed. */
export function thumbnailDisplayUrl(path: string | null | undefined): string | null {
  const resolved = resolveMediaUrl(path);
  if (!resolved) return null;

  if (shouldProxyExternalImage(resolved)) {
    return `${getApiBase()}/api/image-proxy?url=${encodeURIComponent(resolved)}`;
  }

  return resolved;
}
