export function parseApiErrorDetail(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return "";

  try {
    const parsed = JSON.parse(trimmed) as { detail?: unknown };
    if (typeof parsed.detail === "string") {
      return parsed.detail;
    }
    if (Array.isArray(parsed.detail)) {
      return parsed.detail
        .map((item) => {
          if (typeof item === "string") return item;
          if (item && typeof item === "object" && "msg" in item) {
            return String((item as { msg?: unknown }).msg ?? "");
          }
          return "";
        })
        .filter(Boolean)
        .join(" ");
    }
  } catch {
    // Fall through to raw text.
  }

  return trimmed;
}

export function mapGoogleSignInError(status: number, detail: string): string {
  const message = detail.trim();

  if (status === 401) {
    return (
      message ||
      "Google sign-in could not be verified. Confirm GOOGLE_CLIENT_ID matches on the frontend and backend."
    );
  }

  if (status === 403) {
    return message || "This Google account is not authorized to edit CultureGraph.";
  }

  if (status === 503) {
    return (
      message ||
      "CultureGraph sign-in is not configured on the server. Check JWT_SECRET, ADMIN_EMAILS, and GOOGLE_CLIENT_ID."
    );
  }

  if (status >= 500) {
    return message || "CultureGraph server error during sign-in. Try again shortly.";
  }

  return message || `Sign-in failed with status ${status}.`;
}

export function mapSignInTransportError(error: unknown): string {
  if (error instanceof DOMException && error.name === "AbortError") {
    return (
      "Sign-in timed out while contacting the CultureGraph API. " +
      "Check NEXT_PUBLIC_API_URL and confirm the backend is reachable."
    );
  }

  if (error instanceof TypeError) {
    return (
      "Could not reach the CultureGraph API. " +
      "Check NEXT_PUBLIC_API_URL, CORS_ORIGINS, and that the backend is deployed."
    );
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Sign-in failed unexpectedly.";
}

export const GOOGLE_SESSION_ERROR =
  "Sign-in completed with Google, but CultureGraph could not create an app session.";
