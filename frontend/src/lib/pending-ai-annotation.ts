import type { AiSuggestedAnnotation } from "@/lib/types";

export const PENDING_AI_ANNOTATION_KEY = "culturegraph:pending-ai-annotation";

export function setPendingAiAnnotation(
  artworkId: number,
  suggestion: AiSuggestedAnnotation
): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(
    `${PENDING_AI_ANNOTATION_KEY}:${artworkId}`,
    JSON.stringify(suggestion)
  );
}

export function consumePendingAiAnnotation(artworkId: number): AiSuggestedAnnotation | null {
  if (typeof window === "undefined") return null;
  const key = `${PENDING_AI_ANNOTATION_KEY}:${artworkId}`;
  const raw = sessionStorage.getItem(key);
  if (!raw) return null;
  sessionStorage.removeItem(key);
  try {
    return JSON.parse(raw) as AiSuggestedAnnotation;
  } catch {
    return null;
  }
}

export function clearPendingAiAnnotation(artworkId: number): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(`${PENDING_AI_ANNOTATION_KEY}:${artworkId}`);
}
