import { describe, expect, it } from "vitest";

import { GOOGLE_SIGN_IN_COOP, securityResponseHeaders } from "@/lib/security-headers";

describe("security-headers", () => {
  it("allows Google sign-in popup postMessage", () => {
    expect(GOOGLE_SIGN_IN_COOP).toBe("same-origin-allow-popups");
  });

  it("exposes COOP on all routes via next.config", () => {
    const coop = securityResponseHeaders.find(
      (header) => header.key === "Cross-Origin-Opener-Policy"
    );
    expect(coop?.value).toBe("same-origin-allow-popups");
  });
});
