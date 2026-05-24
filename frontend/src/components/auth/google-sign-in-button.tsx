"use client";

import { GoogleLogin, type CredentialResponse } from "@react-oauth/google";
import { useState } from "react";

import { useAuth } from "@/contexts/auth-context";
import { cn } from "@/lib/utils";

interface GoogleSignInButtonProps {
  className?: string;
}

export function GoogleSignInButton({ className }: GoogleSignInButtonProps) {
  const { googleConfigured, signInWithGoogleToken } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (!googleConfigured) {
    return (
      <p className={cn("text-sm text-muted-foreground", className)}>
        Google sign-in is not configured.
      </p>
    );
  }

  async function handleSuccess(response: CredentialResponse) {
    if (!response.credential) {
      setError("Google did not return a sign-in token.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await signInWithGoogleToken(response.credential);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not sign in.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={cn("space-y-2", className)}>
      <GoogleLogin
        onSuccess={(response) => void handleSuccess(response)}
        onError={() => setError("Google sign-in failed.")}
        theme="outline"
        size="large"
        shape="rectangular"
        text="signin_with"
        width="280"
      />
      {loading ? <p className="text-sm text-muted-foreground">Signing in…</p> : null}
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
    </div>
  );
}
