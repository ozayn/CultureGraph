/** Response headers applied to all frontend routes (see next.config.ts). */

export const GOOGLE_SIGN_IN_COOP = "same-origin-allow-popups" as const;

export const securityResponseHeaders = [
  {
    key: "Cross-Origin-Opener-Policy",
    value: GOOGLE_SIGN_IN_COOP,
  },
] as const;
