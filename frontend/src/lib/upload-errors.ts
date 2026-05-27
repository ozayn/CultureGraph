import { ARTWORK_UPLOAD_MAX_BYTES } from "@/lib/upload-validation";

export type UploadErrorKind =
  | "connection"
  | "timeout"
  | "too_large"
  | "unsupported"
  | "upload"
  | "save"
  | "unknown";

export interface FriendlyUploadError {
  kind: UploadErrorKind;
  message: string;
  canRetry: boolean;
}

const RAW_FETCH_PATTERNS = [
  /^failed to fetch$/i,
  /^networkerror/i,
  /^load failed$/i,
  /^network request failed$/i,
];

export function isRawFetchMessage(message: string): boolean {
  return RAW_FETCH_PATTERNS.some((pattern) => pattern.test(message.trim()));
}

export function mapUploadError(
  error: unknown,
  context: "upload" | "save" = "save"
): FriendlyUploadError {
  const fallback =
    context === "upload"
      ? {
          kind: "upload" as const,
          message: "Could not upload image.",
          canRetry: true,
        }
      : {
          kind: "save" as const,
          message: "Could not save artwork.",
          canRetry: true,
        };

  if (error instanceof DOMException && error.name === "AbortError") {
    return {
      kind: "timeout",
      message: "Connection timed out — try again.",
      canRetry: true,
    };
  }

  if (error instanceof TypeError) {
    const message = error.message.trim();
    if (isRawFetchMessage(message) || message.includes("fetch")) {
      return {
        kind: "connection",
        message: "Connection issue — try again.",
        canRetry: true,
      };
    }
  }

  if (error instanceof Error) {
    const message = error.message.trim();
    if (isRawFetchMessage(message)) {
      return {
        kind: "connection",
        message: "Connection issue — try again.",
        canRetry: true,
      };
    }

    if (/timed out/i.test(message)) {
      return {
        kind: "timeout",
        message: "Connection timed out — try again.",
        canRetry: true,
      };
    }

    if (/413|too large|10\s*mb/i.test(message)) {
      return {
        kind: "too_large",
        message: "Image too large.",
        canRetry: false,
      };
    }

    if (/415|jpeg|png|webp|unsupported/i.test(message)) {
      return {
        kind: "unsupported",
        message: "Upload a JPEG, PNG, or WebP image.",
        canRetry: false,
      };
    }

    if (/NEXT_PUBLIC_API_URL|API returned HTML/i.test(message)) {
      return {
        kind: "connection",
        message: "Could not reach the server — check your connection.",
        canRetry: true,
      };
    }

    if (context === "upload") {
      return {
        kind: "upload",
        message: message.length > 120 ? "Could not upload image." : message,
        canRetry: true,
      };
    }

    return {
      kind: "save",
      message: message.length > 120 ? "Could not save artwork." : message,
      canRetry: true,
    };
  }

  return fallback;
}

export function mapValidationUploadError(message: string): FriendlyUploadError {
  if (/10\s*mb|too large/i.test(message)) {
    return { kind: "too_large", message: "Image too large.", canRetry: false };
  }
  if (/jpeg|png|webp/i.test(message)) {
    return { kind: "unsupported", message, canRetry: false };
  }
  return { kind: "unknown", message, canRetry: false };
}

export function logUploadError(context: string, error: unknown): void {
  if (process.env.NODE_ENV === "production") return;
  console.error(`[upload] ${context}`, error);
}

export function maxUploadBytesLabel(): string {
  return `${Math.round(ARTWORK_UPLOAD_MAX_BYTES / (1024 * 1024))} MB`;
}
