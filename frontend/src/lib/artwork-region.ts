import type { Artwork } from "@/lib/types";

export interface ArtworkImageRegion {
  x_percent: number;
  y_percent: number;
  width_percent: number;
  height_percent: number;
}

export const DEFAULT_ARTWORK_REGION: ArtworkImageRegion = {
  x_percent: 8,
  y_percent: 8,
  width_percent: 84,
  height_percent: 84,
};

const MIN_SIZE = 5;

export function clampArtworkRegion(region: ArtworkImageRegion): ArtworkImageRegion {
  let width_percent = Math.max(MIN_SIZE, Math.min(region.width_percent, 100));
  let height_percent = Math.max(MIN_SIZE, Math.min(region.height_percent, 100));
  const x_percent = Math.max(0, Math.min(region.x_percent, 100 - width_percent));
  const y_percent = Math.max(0, Math.min(region.y_percent, 100 - height_percent));
  return { x_percent, y_percent, width_percent, height_percent };
}

export function artworkHasImageRegion(
  artwork: Pick<
    Artwork,
    "crop_x_percent" | "crop_y_percent" | "crop_width_percent" | "crop_height_percent"
  >
): boolean {
  return (
    artwork.crop_x_percent != null &&
    artwork.crop_y_percent != null &&
    artwork.crop_width_percent != null &&
    artwork.crop_height_percent != null
  );
}

export function artworkRegionFromArtwork(
  artwork: Pick<
    Artwork,
    "crop_x_percent" | "crop_y_percent" | "crop_width_percent" | "crop_height_percent"
  >
): ArtworkImageRegion | null {
  if (!artworkHasImageRegion(artwork)) return null;
  return clampArtworkRegion({
    x_percent: artwork.crop_x_percent ?? 0,
    y_percent: artwork.crop_y_percent ?? 0,
    width_percent: artwork.crop_width_percent ?? 100,
    height_percent: artwork.crop_height_percent ?? 100,
  });
}

export function artworkSourceImageUrl(
  artwork: Pick<Artwork, "image_master_url" | "image_url">
): string | null {
  return artwork.image_master_url ?? artwork.image_url;
}
