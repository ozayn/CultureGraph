import { thumbnailDisplayUrl } from "@/lib/media-url";
import type { Artwork, CulturalEntity, CulturalEntityType } from "@/lib/types";

export function artworkThumbnailUrl(
  artwork: Pick<Artwork, "image_thumbnail_url" | "image_url">
): string | null {
  return artwork.image_thumbnail_url ?? artwork.image_url ?? null;
}

/** Resolved src for cards/lists (API base + optional museum proxy). */
export function artworkThumbnailSrc(
  artwork: Pick<Artwork, "image_thumbnail_url" | "image_url">
): string | null {
  return thumbnailDisplayUrl(artworkThumbnailUrl(artwork));
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
