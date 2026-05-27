import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api-config", () => ({
  getApiBase: () => "https://api.example.com",
  apiUrl: (path: string) =>
    `https://api.example.com${path.startsWith("/") ? path : `/${path}`}`,
}));

import {
  resolveMediaUrl,
  shouldProxyExternalImage,
  thumbnailDisplayUrl,
} from "@/lib/media-url";

describe("resolveMediaUrl", () => {
  it("prefixes relative upload paths with the API base", () => {
    expect(resolveMediaUrl("/uploads/artworks/1/thumb.webp")).toBe(
      "https://api.example.com/uploads/artworks/1/thumb.webp"
    );
  });

  it("preserves absolute https museum URLs", () => {
    expect(
      resolveMediaUrl("https://ids.si.edu/ids/download?id=SAAM-1_thumb")
    ).toBe("https://ids.si.edu/ids/download?id=SAAM-1_thumb");
  });

  it("encodes paths with spaces", () => {
    expect(resolveMediaUrl("/uploads/art works/thumb.webp")).toBe(
      "https://api.example.com/uploads/art%20works/thumb.webp"
    );
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

describe("shouldProxyExternalImage", () => {
  it("matches NGA and Smithsonian hosts", () => {
    expect(shouldProxyExternalImage("https://api.nga.gov/iiif/x/full/!200,200/0/default.jpg")).toBe(
      true
    );
    expect(shouldProxyExternalImage("https://ids.si.edu/ids/download?id=1")).toBe(true);
    expect(shouldProxyExternalImage("https://example.com/x.jpg")).toBe(false);
  });
});
