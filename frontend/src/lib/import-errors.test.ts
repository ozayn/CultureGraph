import { describe, expect, it } from "vitest";

import {
  IMPORT_ABORT_MESSAGE,
  isImportAbortError,
  mapImportRequestError,
} from "@/lib/import-errors";

describe("import-errors", () => {
  it("detects AbortError by name", () => {
    expect(isImportAbortError(new DOMException("signal is aborted without reason", "AbortError"))).toBe(
      true
    );
  });

  it("detects aborted signal messages", () => {
    expect(isImportAbortError(new Error("signal is aborted without reason"))).toBe(true);
  });

  it("maps abort errors to import timeout guidance", () => {
    expect(
      mapImportRequestError(new DOMException("signal is aborted without reason", "AbortError"))
    ).toBe(IMPORT_ABORT_MESSAGE);
  });
});
