export const IMPORT_ABORT_MESSAGE =
  "Import took longer than expected. Try a shorter note or run extraction again.";

export function isImportAbortError(error: unknown): boolean {
  if (error instanceof DOMException && error.name === "AbortError") {
    return true;
  }

  if (error instanceof Error) {
    if (error.name === "AbortError") {
      return true;
    }

    const message = error.message.toLowerCase();
    return message.includes("signal is aborted") || message.includes("aborted");
  }

  return false;
}

export function mapImportRequestError(error: unknown): string {
  if (isImportAbortError(error)) {
    return IMPORT_ABORT_MESSAGE;
  }

  if (error instanceof Error) {
    const message = error.message.trim();
    if (message.includes("unexpected shape") || message.includes("could not be parsed")) {
      return "AI extraction returned an unexpected shape. Try again or use local fallback.";
    }
    return message || "Could not extract entries.";
  }

  return "Could not extract entries.";
}
