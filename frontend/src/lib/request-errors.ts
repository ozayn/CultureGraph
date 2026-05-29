export const REQUEST_ABORT_MESSAGE =
  "This took longer than expected. Try again or narrow the search.";

export function isRequestAbortError(error: unknown): boolean {
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

export function mapRequestError(error: unknown, fallback = "Request failed."): string {
  if (isRequestAbortError(error)) {
    return REQUEST_ABORT_MESSAGE;
  }

  if (error instanceof Error) {
    const message = error.message.trim();
    return message || fallback;
  }

  return fallback;
}
