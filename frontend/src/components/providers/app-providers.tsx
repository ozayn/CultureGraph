"use client";

import { GoogleOAuthProvider } from "@react-oauth/google";

import { AuthProvider } from "@/contexts/auth-context";

const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID?.trim() ?? "";

export function AppProviders({ children }: { children: React.ReactNode }) {
  const googleConfigured = Boolean(googleClientId);

  if (!googleConfigured) {
    return <AuthProvider googleConfigured={false}>{children}</AuthProvider>;
  }

  return (
    <GoogleOAuthProvider clientId={googleClientId}>
      <AuthProvider googleConfigured={true}>{children}</AuthProvider>
    </GoogleOAuthProvider>
  );
}
