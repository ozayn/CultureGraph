"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { AnnotationPinForm } from "@/components/annotations/annotation-pin-form";
import { Badge } from "@/components/ui/badge";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { Button } from "@/components/ui/button";
import type { AnnotationPinFormValues } from "@/lib/annotation-form";
import { api } from "@/lib/api";
import { buildAnnotationTagSuggestions } from "@/lib/annotation-suggestions";
import { setPendingAiAnnotation } from "@/lib/pending-ai-annotation";
import {
  formValuesToSuggestedAnnotation,
  hasSuggestedCoordinates,
  suggestedAnnotationToAnnotationPayload,
  suggestedAnnotationToFormValues,
} from "@/lib/research-suggestions";
import { CATEGORY_LABELS, type AiSuggestedAnnotation, type CulturalEntity } from "@/lib/types";

interface AiSuggestedAnnotationsProps {
  artworkId: number;
  suggestions: AiSuggestedAnnotation[];
  culturalEntities?: CulturalEntity[];
  hasImage?: boolean;
  onSuggestionsChange: (suggestions: AiSuggestedAnnotation[]) => void;
}

interface IndexedSuggestion {
  id: string;
  suggestion: AiSuggestedAnnotation;
}

function suggestionId(suggestion: AiSuggestedAnnotation, index: number): string {
  return `${suggestion.category}-${suggestion.note.slice(0, 24)}-${index}`;
}

export function AiSuggestedAnnotations({
  artworkId,
  suggestions,
  culturalEntities = [],
  hasImage = false,
  onSuggestionsChange,
}: AiSuggestedAnnotationsProps) {
  const router = useRouter();
  const [savingId, setSavingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<IndexedSuggestion | null>(null);
  const [editValues, setEditValues] = useState<AnnotationPinFormValues | null>(null);

  const tagSuggestions = useMemo(
    () => buildAnnotationTagSuggestions(culturalEntities),
    [culturalEntities]
  );

  const indexedSuggestions = useMemo(
    () =>
      suggestions.map((suggestion, index) => ({
        id: suggestionId(suggestion, index),
        suggestion,
      })),
    [suggestions]
  );

  function removeSuggestion(id: string) {
    onSuggestionsChange(
      indexedSuggestions
        .filter((item) => item.id !== id)
        .map((item) => item.suggestion)
    );
  }

  async function acceptSuggestion(item: IndexedSuggestion) {
    const { suggestion } = item;
    if (!hasSuggestedCoordinates(suggestion)) {
      setError("Place this suggestion on the image before saving.");
      return;
    }

    setSavingId(item.id);
    setError(null);
    try {
      await api.post(
        `/api/artworks/${artworkId}/annotations`,
        suggestedAnnotationToAnnotationPayload(suggestion, {
          x_percent: suggestion.suggested_position.x_percent,
          y_percent: suggestion.suggested_position.y_percent,
        })
      );
      removeSuggestion(item.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save annotation.");
    } finally {
      setSavingId(null);
    }
  }

  function dismissSuggestion(id: string) {
    removeSuggestion(id);
  }

  function startEdit(item: IndexedSuggestion) {
    setEditing(item);
    setEditValues(suggestedAnnotationToFormValues(item.suggestion));
    setError(null);
  }

  function saveEdit() {
    if (!editing || !editValues) return;
    const updated = formValuesToSuggestedAnnotation(editValues, editing.suggestion);
    onSuggestionsChange(
      indexedSuggestions.map((item) =>
        item.id === editing.id ? updated : item.suggestion
      )
    );
    setEditing(null);
    setEditValues(null);
  }

  function placeOnImage(item: IndexedSuggestion) {
    setPendingAiAnnotation(artworkId, item.suggestion);
    router.push(`/artworks/${artworkId}/annotate`);
  }

  if (indexedSuggestions.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      <div>
        <h4 className="mb-1 font-medium">AI suggested annotations</h4>
        <p className="text-sm text-muted-foreground">
          Suggested by AI — review before saving.
        </p>
      </div>

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <ul className="space-y-3">
        {indexedSuggestions.map((item) => {
          const { suggestion } = item;
          const positioned = hasSuggestedCoordinates(suggestion);
          return (
            <li
              key={item.id}
              className="space-y-3 rounded-xl border border-border bg-muted/20 p-4"
            >
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="secondary">{CATEGORY_LABELS[suggestion.category]}</Badge>
                <span className="text-xs text-muted-foreground">
                  {Math.round(suggestion.confidence * 100)}% confidence
                </span>
                {positioned ? (
                  <span className="text-xs text-muted-foreground">
                    Pin at {suggestion.suggested_position.x_percent?.toFixed(0)}%,{" "}
                    {suggestion.suggested_position.y_percent?.toFixed(0)}%
                  </span>
                ) : (
                  <span className="text-xs text-muted-foreground">No pin location yet</span>
                )}
              </div>

              <p className="text-sm leading-relaxed text-foreground">{suggestion.note}</p>

              {suggestion.tags.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {suggestion.tags.map((tag) => (
                    <Badge key={tag} variant="outline" className="text-[11px] font-normal">
                      {tag}
                    </Badge>
                  ))}
                </div>
              ) : null}

              {suggestion.linked_concept_names.length > 0 ? (
                <p className="text-xs text-muted-foreground">
                  Concepts: {suggestion.linked_concept_names.join(" · ")}
                </p>
              ) : null}

              {suggestion.suggested_position.reason ? (
                <p className="text-xs leading-relaxed text-muted-foreground">
                  {suggestion.suggested_position.reason}
                </p>
              ) : null}

              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  size="sm"
                  className="min-h-10"
                  disabled={!positioned || savingId === item.id}
                  onClick={() => void acceptSuggestion(item)}
                >
                  {savingId === item.id ? "Saving…" : "Accept"}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="min-h-10"
                  onClick={() => startEdit(item)}
                >
                  Edit
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="min-h-10"
                  onClick={() => dismissSuggestion(item.id)}
                >
                  Dismiss
                </Button>
                {!positioned && hasImage ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="min-h-10"
                    onClick={() => placeOnImage(item)}
                  >
                    Place on image
                  </Button>
                ) : null}
                {!positioned && !hasImage ? (
                  <span className="self-center text-xs text-muted-foreground">
                    Add an artwork photo to place this pin.
                  </span>
                ) : null}
              </div>
            </li>
          );
        })}
      </ul>

      {hasImage ? (
        <p className="text-xs text-muted-foreground">
          Or open{" "}
          <Link
            href={`/artworks/${artworkId}/annotate`}
            className="underline-offset-2 hover:underline"
          >
            annotate
          </Link>{" "}
          to place suggestions manually.
        </p>
      ) : null}

      <BottomSheet
        open={editing !== null}
        onOpenChange={(open) => {
          if (!open) {
            setEditing(null);
            setEditValues(null);
          }
        }}
        title="Edit AI suggestion"
        description="Adjust the note, tags, or links before accepting."
      >
        {editValues ? (
          <>
            <AnnotationPinForm
              values={editValues}
              onChange={setEditValues}
              culturalEntities={culturalEntities}
              tagSuggestions={tagSuggestions}
              noteId="edit-ai-suggestion-note"
            />
            <Button type="button" size="touch" className="mt-4 w-full" onClick={saveEdit}>
              Save edits
            </Button>
          </>
        ) : null}
      </BottomSheet>
    </div>
  );
}
