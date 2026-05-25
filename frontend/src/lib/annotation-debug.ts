export function logAnnotationRequest(endpoint: string, payload: unknown): void {
  if (process.env.NODE_ENV !== "development") {
    return;
  }

  console.info("[CultureGraph annotation]", { endpoint, payload });
}
