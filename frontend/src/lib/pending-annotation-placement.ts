const PENDING_ANNOTATION_PLACEMENT_KEY = "culturegraph:pending-annotation-placement";

export function setPendingAnnotationPlacement(artworkId: number, annotationId: number): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(
    `${PENDING_ANNOTATION_PLACEMENT_KEY}:${artworkId}`,
    String(annotationId)
  );
}

export function consumePendingAnnotationPlacement(artworkId: number): number | null {
  if (typeof window === "undefined") return null;
  const key = `${PENDING_ANNOTATION_PLACEMENT_KEY}:${artworkId}`;
  const raw = sessionStorage.getItem(key);
  if (!raw) return null;
  sessionStorage.removeItem(key);
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

export function clearPendingAnnotationPlacement(artworkId: number): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(`${PENDING_ANNOTATION_PLACEMENT_KEY}:${artworkId}`);
}
