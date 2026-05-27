import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api-config", () => ({
  getApiBase: () => "https://api.example.com",
  apiUrl: (path: string) =>
    `https://api.example.com${path.startsWith("/") ? path : `/${path}`}`,
}));

import {
  displayImageUrl,
  resolveImageUrl,
  shouldProxyExternalImage,
  thumbnailDisplayUrl,
} from "@/lib/media-url";

describe("resolveImageUrl", () => {
  it("prefixes /uploads paths with the API base", () => {
    expect(resolveImageUrl("/uploads/artworks/1/thumb.webp")).toBe(
      "https://api.example.com/uploads/artworks/1/thumb.webp"
    );
  });

  it("prefixes upload paths missing a leading slash", () => {
    expect(resolveImageUrl("uploads/artworks/1/thumb.webp")).toBe(
      "https://api.example.com/uploads/artworks/1/thumb.webp"
    );
  });

  it("preserves absolute https museum URLs", () => {
    expect(
      resolveImageUrl("https://ids.si.edu/ids/download?id=SAAM-1_thumb")
    ).toBe("https://ids.si.edu/ids/download?id=SAAM-1_thumb");
  });

  it("encodes paths with spaces", () => {
    expect(resolveImageUrl("/uploads/art works/thumb.webp")).toBe(
      "https://api.example.com/uploads/art%20works/thumb.webp"
    );
  });

  it("returns null for empty values", () => {
    expect(resolveImageUrl(null)).toBeNull();
    expect(resolveImageUrl("  ")).toBeNull();
  });
});

describe("thumbnailDisplayUrl", () => {
  it("proxies Smithsonian thumbnails through the API", () => {
    const url = thumbnailDisplayUrl(
      "https://ids.si.edu/ids/download?id=SAAM-1_thumb"
    );
    expect(url).toBe(
      "https://api.example.com/api/image-proxy?url=" +
        encodeURIComponent("https://ids.si.edu/ids/download?id=SAAM-1_thumb")
    );
  });

  it("does not proxy same-origin uploads", () => {
    expect(thumbnailDisplayUrl("/uploads/artworks/1/thumb.webp")).toBe(
      "https://api.example.com/uploads/artworks/1/thumb.webp"
    );
  });
});

describe("displayImageUrl", () => {
  it("resolves uploaded display images on the API host", () => {
    expect(displayImageUrl("/uploads/artworks/9/abc_display.webp")).toBe(
      "https://api.example.com/uploads/artworks/9/abc_display.webp"
    );
  });
});

describe("shouldProxyExternalImage", () => {
  it("matches NGA and Smithsonian hosts", () => {
    expect(shouldProxyExternalImage("https://api.nga.gov/iiif/x/full/!200,200/0/default.jpg")).toBe(
      true
    );
    expect(shouldProxyExternalImage("https://ids.si.edu/ids/download?id=1")).toBe(true);
    expect(shouldProxyExternalImage("https://example.com/x.jpg")).toBe(false);
    expect(shouldProxyExternalImage("https://api.example.com/uploads/1.webp")).toBe(false);
  });
});
