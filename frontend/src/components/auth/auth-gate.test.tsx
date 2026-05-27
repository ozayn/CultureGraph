import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AuthGate } from "@/components/auth/auth-gate";
import { SignInInlineHint } from "@/components/auth/sign-in-inline-hint";

vi.mock("@/components/auth/google-sign-in-button", () => ({
  GoogleSignInButton: () => <button type="button">Google sign-in</button>,
}));

describe("AuthGate", () => {
  it("shows browse vs edit copy once", () => {
    render(<AuthGate />);
    expect(
      screen.getByText(
        /Anyone can browse\. Approved accounts can edit, annotate, upload, and run AI research\./
      )
    ).toBeInTheDocument();
    expect(screen.queryByText(/Sign in to edit CultureGraph/i)).not.toBeInTheDocument();
  });
});

describe("SignInInlineHint", () => {
  it("renders preset research hint", () => {
    render(<SignInInlineHint hint="research" />);
    expect(screen.getByText("Sign in to use AI research.")).toBeInTheDocument();
  });
});
