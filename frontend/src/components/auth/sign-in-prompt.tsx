"use client";

import { GoogleSignInButton } from "@/components/auth/google-sign-in-button";
import { cn } from "@/lib/utils";

interface SignInPromptProps {
  className?: string;
  compact?: boolean;
}

export function SignInPrompt({ className, compact }: SignInPromptProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-card p-4 sm:p-5",
        compact ? "space-y-3" : "space-y-4",
        className
      )}
    >
      <div className="space-y-1">
        <p className="font-heading text-lg">Sign in to edit CultureGraph.</p>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Anyone can browse visits and artworks. Only approved accounts can create, import, upload,
          annotate, or run AI research.
        </p>
      </div>
      <GoogleSignInButton />
    </div>
  );
}
