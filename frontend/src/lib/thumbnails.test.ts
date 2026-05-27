import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api-config", () => ({
  getApiBase: () => "https://api.example.com",
  apiUrl: (path: string) =>
    `https://api.example.com${path.startsWith("/") ? path : `/${path}`}`,
}));

import {
  artworkDisplaySrc,
  artworkThumbnailSrc,
  pickArtworkDisplayRaw,
  pickArtworkThumbnailRaw,
} from "@/lib/thumbnails";

describe("artwork image precedence", () => {
  const artwork = {
    image_thumbnail_url: "/uploads/artworks/1/thumb.webp",
    image_url: "/uploads/artworks/1/display.webp",
    catalog_thumbnail_url: "https://example.com/catalog-thumb.jpg",
    catalog_image_url: "https://example.com/catalog-full.jpg",
  };

  it("prefers thumbnail fields for cards", () => {
    expect(pickArtworkThumbnailRaw(artwork)).toBe("/uploads/artworks/1/thumb.webp");
    expect(artworkThumbnailSrc(artwork)).toBe(
      "https://api.example.com/uploads/artworks/1/thumb.webp"
    );
  });

  it("prefers display image_url for hero", () => {
    expect(pickArtworkDisplayRaw(artwork)).toBe("/uploads/artworks/1/display.webp");
    expect(artworkDisplaySrc(artwork)).toBe(
      "https://api.example.com/uploads/artworks/1/display.webp"
    );
  });

  it("falls back to catalog URLs when uploads missing", () => {
    const officialOnly = {
      image_thumbnail_url: null,
      image_url: null,
      catalog_thumbnail_url: "https://api.nga.gov/iiif/u/full/!200,200/0/default.jpg",
      catalog_image_url: "https://api.nga.gov/iiif/u/full/!1600,1600/0/default.jpg",
    };
    expect(pickArtworkThumbnailRaw(officialOnly)).toContain("200,200");
    expect(pickArtworkDisplayRaw(officialOnly)).toContain("1600");
  });
});
