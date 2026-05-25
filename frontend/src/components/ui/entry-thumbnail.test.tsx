import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { EntryThumbnail } from "@/components/ui/entry-thumbnail";

describe("EntryThumbnail", () => {
  afterEach(() => {
    cleanup();
  });
  it("renders image with alt text when imageUrl is provided", () => {
    render(
      <EntryThumbnail
        imageUrl="https://example.com/thumb.jpg"
        alt="Starry Night"
        entityType="artwork"
      />
    );

    expect(screen.getByRole("img", { name: "Starry Night" })).toBeInTheDocument();
  });

  it("renders type fallback icon when no image is available", () => {
    render(<EntryThumbnail entityType="artist" alt="" />);

    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText("Artist")).toHaveClass("sr-only");
  });
});
