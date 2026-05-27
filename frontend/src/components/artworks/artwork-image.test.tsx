import { cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ArtworkImage } from "@/components/artworks/artwork-image";

vi.mock("@/lib/media-url", () => ({
  displayImageUrl: (url: string | null | undefined) =>
    url ? `https://api.example.com${url.startsWith("/") ? url : `/${url}`}` : null,
}));

describe("ArtworkImage", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders resolved upload URL", () => {
    render(<ArtworkImage imageUrl="/uploads/artworks/1/display.webp" />);
    const image = document.querySelector("img");
    expect(image).toHaveAttribute(
      "src",
      "https://api.example.com/uploads/artworks/1/display.webp"
    );
    expect(image).toHaveAttribute("alt", "");
  });

  it("shows placeholder when image fails to load", () => {
    const { container } = render(
      <ArtworkImage imageUrl="/uploads/artworks/1/missing.webp" />
    );
    const image = document.querySelector("img");
    expect(image).toBeTruthy();
    fireEvent.error(image!);
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("svg")).toBeTruthy();
  });
});
