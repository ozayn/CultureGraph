import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { prepareArtworkUploadFile } from "@/lib/prepare-artwork-upload";

describe("prepareArtworkUploadFile", () => {
  const OriginalImage = globalThis.Image;

  beforeEach(() => {
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:test"),
      revokeObjectURL: vi.fn(),
    });
    class MockImage {
      naturalWidth = 800;
      naturalHeight = 600;
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      set src(_value: string) {
        queueMicrotask(() => this.onload?.());
      }
    }
    vi.stubGlobal("Image", MockImage as unknown as typeof Image);
  });

  afterEach(() => {
    vi.stubGlobal("Image", OriginalImage);
  });

  it("passes through small images without re-encoding", async () => {
    const file = new File(["small"], "gallery.jpg", {
      type: "image/jpeg",
      lastModified: 1_700_000_000_000,
    });

    const result = await prepareArtworkUploadFile(file);

    expect(result.wasNormalized).toBe(false);
    expect(result.file).toBe(file);
    expect(result.outputSize).toBe(file.size);
  });
});
