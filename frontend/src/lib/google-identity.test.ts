import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  initializeGoogleIdentityOnce,
  isGoogleIdentityInitialized,
  resetGoogleIdentityForTests,
} from "@/lib/google-identity";

describe("google-identity", () => {
  beforeEach(() => {
    resetGoogleIdentityForTests();
    window.google = {
      accounts: {
        id: {
          initialize: vi.fn(),
          renderButton: vi.fn(),
          prompt: vi.fn(),
        },
      },
    };
  });

  it("initializes Google Identity Services only once per client id", () => {
    initializeGoogleIdentityOnce("client-a");
    initializeGoogleIdentityOnce("client-a");

    expect(window.google?.accounts.id.initialize).toHaveBeenCalledTimes(1);
    expect(isGoogleIdentityInitialized("client-a")).toBe(true);
  });
});
