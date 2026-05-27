import { api } from "@/lib/api";
import {
  markSuggestionAccepted,
  parseSuggestedAnnotations,
  suggestionMatchKey,
} from "@/lib/research-suggestions";
import type { AiSuggestedAnnotation } from "@/lib/types";

/**
 * After placing an AI suggestion on the annotate page, mark it accepted on the
 * latest research note so it no longer appears as pending after reload.
 */
export async function persistAcceptedAiSuggestion(
  artworkId: number,
  suggestion: AiSuggestedAnnotation,
  annotationId: number
): Promise<void> {
  const notes = await api.get<
    { id: number; suggested_annotations: string }[]
  >(`/api/artworks/${artworkId}/research`);

  const note = notes[0];
  if (!note) return;

  const parsed = parseSuggestedAnnotations(note.suggested_annotations);
  const key = suggestionMatchKey(suggestion);
  const hasMatch = parsed.some((item) => suggestionMatchKey(item) === key);
  if (!hasMatch) return;

  const updated = markSuggestionAccepted(parsed, suggestion, annotationId);
  await api.patch(`/api/artworks/${artworkId}/research/${note.id}/suggestions`, {
    suggested_annotations: updated,
  });
}
