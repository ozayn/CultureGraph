"use client";

import { GoogleSignInButton } from "@/components/auth/google-sign-in-button";
import { cn } from "@/lib/utils";

interface AuthGateProps {
  className?: string;
}

/** Single page-level sign-in prompt for logged-out viewers on editable pages. */
export function AuthGate({ className }: AuthGateProps) {
  return (
    <section
      className={cn(
        "rounded-lg border border-border/60 bg-muted/20 px-4 py-3",
        className
      )}
      aria-label="Sign in to edit"
    >
      <p className="text-sm leading-relaxed text-muted-foreground">
        Anyone can browse. Approved accounts can edit, annotate, upload, and run AI research.
      </p>
      <div className="mt-3 max-w-xs">
        <GoogleSignInButton />
      </div>
    </section>
  );
}
