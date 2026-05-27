import { describe, expect, it } from "vitest";

import {
  isRawFetchMessage,
  mapUploadError,
  mapValidationUploadError,
} from "@/lib/upload-errors";

describe("upload-errors", () => {
  it("detects raw fetch failure messages", () => {
    expect(isRawFetchMessage("Failed to fetch")).toBe(true);
    expect(isRawFetchMessage("NetworkError when attempting to fetch resource.")).toBe(
      true
    );
    expect(isRawFetchMessage("Something else")).toBe(false);
  });

  it("maps TypeError fetch failures to connection guidance", () => {
    const mapped = mapUploadError(new TypeError("Failed to fetch"), "upload");
    expect(mapped.message).toBe("Connection issue — try again.");
    expect(mapped.canRetry).toBe(true);
    expect(mapped.kind).toBe("connection");
  });

  it("maps abort errors to timeout guidance", () => {
    const mapped = mapUploadError(
      new DOMException("signal is aborted without reason", "AbortError"),
      "upload"
    );
    expect(mapped.message).toBe("Connection timed out — try again.");
    expect(mapped.canRetry).toBe(true);
  });

  it("maps upload context errors to friendly upload copy", () => {
    expect(mapUploadError(new Error("Failed to fetch"), "upload").message).toBe(
      "Connection issue — try again."
    );
    expect(mapUploadError(new Error("413 payload too large"), "upload").message).toBe(
      "Image too large."
    );
    expect(
      mapUploadError(
        new Error("x".repeat(150)),
        "upload"
      ).message
    ).toBe("Could not upload image.");
  });

  it("maps validation size errors", () => {
    expect(mapValidationUploadError("File must be 10 MB or smaller.").message).toBe(
      "Image too large."
    );
  });
});
