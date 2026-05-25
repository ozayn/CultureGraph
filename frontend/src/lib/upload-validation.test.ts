import { describe, expect, it } from "vitest";

import {
  ARTWORK_UPLOAD_MAX_BYTES,
  formatUploadFileSize,
  validateArtworkUploadFile,
} from "@/lib/upload-validation";

describe("upload-validation", () => {
  it("accepts supported image types under the size limit", () => {
    const file = new File(["abc"], "photo.jpg", { type: "image/jpeg" });
    Object.defineProperty(file, "size", { value: 1024 });
    expect(validateArtworkUploadFile(file)).toBeNull();
  });

  it("rejects unsupported file types", () => {
    const file = new File(["abc"], "notes.txt", { type: "text/plain" });
    expect(validateArtworkUploadFile(file)).toMatch(/JPEG, PNG, or WebP/i);
  });

  it("rejects oversized files", () => {
    const file = new File(["abc"], "photo.png", { type: "image/png" });
    Object.defineProperty(file, "size", { value: ARTWORK_UPLOAD_MAX_BYTES + 1 });
    expect(validateArtworkUploadFile(file)).toMatch(/10 MB/i);
  });

  it("formats file sizes for display", () => {
    expect(formatUploadFileSize(2048)).toBe("2 KB");
    expect(formatUploadFileSize(2 * 1024 * 1024)).toBe("2.0 MB");
  });
});
