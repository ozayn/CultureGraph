"use client";

import { useEffect } from "react";

import { AuthProvider } from "@/contexts/auth-context";
import { GoogleIdentityProvider } from "@/contexts/google-identity-context";
import { logAuthConfigInDevelopment } from "@/lib/auth-debug";

const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID?.trim() ?? "";

export function AppProviders({ children }: { children: React.ReactNode }) {
  const googleConfigured = Boolean(googleClientId);

  useEffect(() => {
    logAuthConfigInDevelopment();
  }, []);

  return (
    <AuthProvider googleConfigured={googleConfigured}>
      {googleConfigured ? (
        <GoogleIdentityProvider clientId={googleClientId}>
          {children}
        </GoogleIdentityProvider>
      ) : (
        children
      )}
    </AuthProvider>
  );
}
