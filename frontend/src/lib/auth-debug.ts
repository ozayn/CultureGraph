import { getApiBase } from "@/lib/api";

let logged = false;

export function logAuthConfigInDevelopment(): void {
  if (process.env.NODE_ENV !== "development" || logged) {
    return;
  }

  logged = true;

  const apiUrl = getApiBase();
  const googleConfigured = Boolean(process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID?.trim());

  console.info("[CultureGraph auth]", {
    apiUrl,
    googleClientIdConfigured: googleConfigured,
  });

  if (typeof window !== "undefined" && apiUrl.replace(/\/+$/, "") === window.location.origin) {
    console.warn(
      "[CultureGraph auth] NEXT_PUBLIC_API_URL matches the web app origin. " +
        "It should point to the CultureGraph API service URL, not the frontend URL."
    );
  }
}
