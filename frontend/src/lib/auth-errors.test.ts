import { describe, expect, it } from "vitest";

import { mapGoogleSignInError, parseApiErrorDetail } from "@/lib/auth-errors";

describe("auth-errors", () => {
  it("parses FastAPI detail strings", () => {
    expect(parseApiErrorDetail('{"detail":"JWT_SECRET is not configured on the server."}')).toBe(
      "JWT_SECRET is not configured on the server."
    );
  });

  it("maps auth status codes to clear messages", () => {
    expect(mapGoogleSignInError(403, "This Google account is not authorized to edit CultureGraph.")).toBe(
      "This Google account is not authorized to edit CultureGraph."
    );
    expect(mapGoogleSignInError(503, "")).toContain("not configured");
  });
});
