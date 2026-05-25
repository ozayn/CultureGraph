"use client";

import { useEffect, useRef } from "react";

import { Button } from "@/components/ui/button";
import { useGoogleIdentity } from "@/contexts/google-identity-context";
import { useAuth } from "@/contexts/auth-context";
import { renderGoogleSignInButton } from "@/lib/google-identity";
import { cn } from "@/lib/utils";

interface GoogleSignInButtonProps {
  className?: string;
  onSignedIn?: () => void;
}

function GoogleSignInButtonInner({ className, onSignedIn }: GoogleSignInButtonProps) {
  const { ready, error: initError } = useGoogleIdentity();
  const { signInError, signInLoading, clearSignInError, canEdit } = useAuth();
  const containerRef = useRef<HTMLDivElement>(null);
  const wasSigningInRef = useRef(false);

  useEffect(() => {
    if (!ready || !containerRef.current) return;

    renderGoogleSignInButton(containerRef.current, {
      theme: "outline",
      size: "large",
      text: "signin_with",
      shape: "rectangular",
      width: 280,
    });
  }, [ready, signInError]);

  useEffect(() => {
    if (signInLoading) {
      wasSigningInRef.current = true;
      return;
    }

    if (wasSigningInRef.current && canEdit) {
      wasSigningInRef.current = false;
      onSignedIn?.();
    }
  }, [canEdit, onSignedIn, signInLoading]);

  return (
    <div className={cn("space-y-3", className)}>
      <div
        ref={containerRef}
        className={cn("min-h-11", signInLoading && "pointer-events-none opacity-60")}
        aria-label="Sign in with Google"
      />
      {!ready && !initError ? (
        <p className="text-sm text-muted-foreground">Loading Google sign-in…</p>
      ) : null}
      {signInLoading ? (
        <p className="text-sm text-muted-foreground">Creating your CultureGraph session…</p>
      ) : null}
      {initError ? <p className="text-sm text-destructive">{initError}</p> : null}
      {signInError ? (
        <div className="space-y-3 rounded-lg border border-border bg-muted/40 p-3">
          <p className="text-sm leading-relaxed text-destructive">{signInError}</p>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="min-h-10"
            onClick={() => clearSignInError()}
          >
            Try again
          </Button>
        </div>
      ) : null}
    </div>
  );
}

export function GoogleSignInButton({ className, onSignedIn }: GoogleSignInButtonProps) {
  const { googleConfigured } = useAuth();

  if (!googleConfigured) {
    return (
      <p className={cn("text-sm text-muted-foreground", className)}>
        Google sign-in is not configured. Set NEXT_PUBLIC_GOOGLE_CLIENT_ID on the web service.
      </p>
    );
  }

  return <GoogleSignInButtonInner className={className} onSignedIn={onSignedIn} />;
}
