import sharp from "sharp";
import { describe, expect, it } from "vitest";

import {
  extractCaptureDateFromJpegBytes,
  extractPhotoCaptureDate,
} from "@/lib/extract-photo-capture-date";

async function makeJpegWithExif(exifDate: string): Promise<Uint8Array> {
  const buffer = await sharp({
    create: {
      width: 8,
      height: 8,
      channels: 3,
      background: { r: 120, g: 80, b: 40 },
    },
  })
    .jpeg()
    .withMetadata({
      exif: {
        IFD0: {
          DateTime: exifDate,
        },
        Exif: {
          DateTimeOriginal: exifDate,
        },
      },
    })
    .toBuffer();

  return new Uint8Array(buffer);
}

describe("extractPhotoCaptureDate", () => {
  it("returns null for non-JPEG files", async () => {
    const file = new File(["png"], "photo.png", { type: "image/png" });
    await expect(extractPhotoCaptureDate(file)).resolves.toBeNull();
  });

  it("reads DateTimeOriginal from JPEG EXIF bytes", async () => {
    const bytes = await makeJpegWithExif("2026:05:23 14:30:00");
    const file = new File([bytes], "photo.jpg", { type: "image/jpeg" });

    await expect(extractPhotoCaptureDate(file)).resolves.toBe("2026-05-23T14:30:00Z");
    expect(extractCaptureDateFromJpegBytes(bytes)).toBe("2026-05-23T14:30:00Z");
  });

  it("returns null when EXIF date is missing", () => {
    const bytes = new Uint8Array([0xff, 0xd8, 0xff, 0xd9]);
    expect(extractCaptureDateFromJpegBytes(bytes)).toBeNull();
  });
});
