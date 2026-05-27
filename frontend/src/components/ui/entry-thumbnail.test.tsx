import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { EntryThumbnail } from "@/components/ui/entry-thumbnail";

describe("EntryThumbnail", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders image when imageUrl is provided", () => {
    render(
      <EntryThumbnail
        imageUrl="https://example.com/thumb.jpg"
        alt="Starry Night"
        entityType="artwork"
      />
    );

    const image = document.querySelector("img");
    expect(image).toHaveAttribute("src", "https://example.com/thumb.jpg");
    expect(image).toHaveAttribute("alt", "");
    expect(image).toHaveAttribute("aria-hidden", "true");
  });

  it("renders type fallback icon when no image is available", () => {
    render(<EntryThumbnail entityType="artist" alt="Claude Monet" />);

    expect(document.querySelector("img")).toBeNull();
    expect(screen.getByRole("img", { name: "Claude Monet" })).toBeInTheDocument();
  });

  it("falls back to placeholder when image fails to load", () => {
    render(
      <EntryThumbnail
        imageUrl="https://example.com/broken.jpg"
        alt="Broken"
        entityType="artwork"
      />
    );

    const image = document.querySelector("img");
    expect(image).toBeTruthy();
    fireEvent.error(image!);

    expect(document.querySelector("img")).toBeNull();
    expect(screen.getByRole("img", { name: "Broken" })).toBeInTheDocument();
  });
});
