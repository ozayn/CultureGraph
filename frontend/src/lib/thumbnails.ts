import { displayImageUrl, thumbnailDisplayUrl } from "@/lib/media-url";
import type { Artwork, CulturalEntity, CulturalEntityType } from "@/lib/types";

export type ArtworkImageFields = {
  image_thumbnail_url?: string | null;
  image_url?: string | null;
  catalog_thumbnail_url?: string | null;
  catalog_image_url?: string | null;
};

/** First valid raw thumbnail path/URL for an artwork (API field precedence). */
export function pickArtworkThumbnailRaw(
  artwork: ArtworkImageFields
): string | null {
  for (const value of [
    artwork.image_thumbnail_url,
    artwork.catalog_thumbnail_url,
    artwork.image_url,
    artwork.catalog_image_url,
  ]) {
    if (value?.trim()) return value.trim();
  }
  return null;
}

/** First valid raw display path/URL for detail hero. */
export function pickArtworkDisplayRaw(artwork: ArtworkImageFields): string | null {
  for (const value of [
    artwork.image_url,
    artwork.catalog_image_url,
    artwork.image_thumbnail_url,
    artwork.catalog_thumbnail_url,
  ]) {
    if (value?.trim()) return value.trim();
  }
  return null;
}

/** @deprecated Use resolveArtworkImageRaw(artwork, "thumbnail") */
export function artworkThumbnailUrl(artwork: ArtworkImageFields): string | null {
  return pickArtworkThumbnailRaw(artwork);
}

/** Resolved src for cards/lists (API base + optional museum proxy). */
export function artworkThumbnailSrc(artwork: ArtworkImageFields): string | null {
  return thumbnailDisplayUrl(pickArtworkThumbnailRaw(artwork));
}

/** Resolved src for artwork detail hero. */
export function artworkDisplaySrc(artwork: ArtworkImageFields): string | null {
  return displayImageUrl(pickArtworkDisplayRaw(artwork));
}

/** Single entry point: raw API fields → browser-ready image URL. */
export function resolveArtworkImageUrl(
  artwork: ArtworkImageFields,
  kind: "thumbnail" | "detail"
): string | null {
  return kind === "thumbnail" ? artworkThumbnailSrc(artwork) : artworkDisplaySrc(artwork);
}

/** Raw path/URL chosen for a given display kind (debugging). */
export function resolveArtworkImageRaw(
  artwork: ArtworkImageFields,
  kind: "thumbnail" | "detail"
): string | null {
  return kind === "thumbnail" ? pickArtworkThumbnailRaw(artwork) : pickArtworkDisplayRaw(artwork);
}

export function entityThumbnailUrl(
  entity: Pick<CulturalEntity, "thumbnail_url" | "image_url">
): string | null {
  return entity.thumbnail_url ?? entity.image_url;
}

export function importDraftThumbnailUrl(
  draft: Pick<{ thumbnail_url?: string | null; image_url?: string | null }, "thumbnail_url" | "image_url">
): string | null {
  return draft.thumbnail_url ?? draft.image_url ?? null;
}

export type ThumbnailEntityType = CulturalEntityType | "artwork";
