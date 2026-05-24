"use client";

import { useEffect, useRef } from "react";

import { useGoogleIdentity } from "@/contexts/google-identity-context";
import { useAuth } from "@/contexts/auth-context";
import { renderGoogleSignInButton } from "@/lib/google-identity";
import { cn } from "@/lib/utils";

interface GoogleSignInButtonProps {
  className?: string;
}

function GoogleSignInButtonInner({ className }: GoogleSignInButtonProps) {
  const { ready, error: initError } = useGoogleIdentity();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ready || !containerRef.current) return;

    renderGoogleSignInButton(containerRef.current, {
      theme: "outline",
      size: "large",
      text: "signin_with",
      shape: "rectangular",
      width: 280,
    });
  }, [ready]);

  return (
    <div className={cn("space-y-2", className)}>
      <div ref={containerRef} className="min-h-11" aria-label="Sign in with Google" />
      {!ready && !initError ? (
        <p className="text-sm text-muted-foreground">Loading Google sign-in…</p>
      ) : null}
      {initError ? <p className="text-sm text-destructive">{initError}</p> : null}
    </div>
  );
}

export function GoogleSignInButton({ className }: GoogleSignInButtonProps) {
  const { googleConfigured } = useAuth();

  if (!googleConfigured) {
    return (
      <p className={cn("text-sm text-muted-foreground", className)}>
        Google sign-in is not configured.
      </p>
    );
  }

  return <GoogleSignInButtonInner className={className} />;
}
