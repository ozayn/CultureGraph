import { describe, expect, it } from "vitest";

import {
  REQUEST_ABORT_MESSAGE,
  isRequestAbortError,
  mapRequestError,
} from "@/lib/request-errors";

describe("request-errors", () => {
  it("detects DOMException abort errors", () => {
    expect(
      isRequestAbortError(new DOMException("signal is aborted without reason", "AbortError"))
    ).toBe(true);
  });

  it("maps abort errors to friendly guidance", () => {
    expect(
      mapRequestError(new DOMException("signal is aborted without reason", "AbortError"))
    ).toBe(REQUEST_ABORT_MESSAGE);
    expect(mapRequestError(new Error("signal is aborted without reason"))).toBe(
      REQUEST_ABORT_MESSAGE
    );
  });

  it("passes through regular errors", () => {
    expect(mapRequestError(new Error("Server unavailable"))).toBe("Server unavailable");
  });
});
