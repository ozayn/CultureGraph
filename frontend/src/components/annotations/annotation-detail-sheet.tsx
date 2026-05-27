"use client";

import { useEffect, useState } from "react";

import { AnnotationPinForm } from "@/components/annotations/annotation-pin-form";
import { AnnotationPinMeta } from "@/components/annotations/annotation-pin-meta";
import { Badge } from "@/components/ui/badge";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { Button } from "@/components/ui/button";
import {
  annotationToFormValues,
  type AnnotationPinFormValues,
} from "@/lib/annotation-form";
import { isPlacedAnnotation } from "@/lib/annotation-placement";
import { CATEGORY_LABELS, type Annotation, type CulturalEntity } from "@/lib/types";

interface AnnotationDetailSheetProps {
  annotation: Annotation | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  canEdit: boolean;
  culturalEntities?: CulturalEntity[];
  tagSuggestions?: string[];
  saving?: boolean;
  error?: string | null;
  success?: string | null;
  onSave: (values: AnnotationPinFormValues) => Promise<void>;
  onDelete: () => void;
  onMovePin?: () => void;
  onPlaceOnImage?: () => void;
}

export function AnnotationDetailSheet({
  annotation,
  open,
  onOpenChange,
  canEdit,
  culturalEntities = [],
  tagSuggestions = [],
  saving = false,
  error = null,
  success = null,
  onSave,
  onDelete,
  onMovePin,
  onPlaceOnImage,
}: AnnotationDetailSheetProps) {
  const [mode, setMode] = useState<"view" | "edit">("view");
  const [draft, setDraft] = useState<AnnotationPinFormValues | null>(null);

  useEffect(() => {
    if (!annotation || !open) return;
    setMode("view");
    setDraft(annotationToFormValues(annotation));
  }, [annotation, open]);

  useEffect(() => {
    if (success) setMode("view");
  }, [success]);

  if (!annotation || !draft) {
    return null;
  }

  const placed = isPlacedAnnotation(annotation);

  function handleCancelEdit() {
    if (!annotation) return;
    setDraft(annotationToFormValues(annotation));
    setMode("view");
  }

  return (
    <BottomSheet
      open={open}
      onOpenChange={onOpenChange}
      title={mode === "edit" ? "Edit annotation" : "Annotation"}
      description={
        mode === "edit"
          ? "Update the note, category, tags, or links."
          : placed
            ? "Pinned on the artwork image."
            : "Not placed on the image yet."
      }
      footer={
        mode === "edit" ? (
          <div className="flex flex-col gap-2">
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
            {success ? <p className="text-sm text-green-700 dark:text-green-400">{success}</p> : null}
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="touch"
                className="flex-1"
                disabled={saving}
                onClick={handleCancelEdit}
              >
                Cancel
              </Button>
              <Button
                type="button"
                size="touch"
                className="flex-1"
                disabled={saving || !draft.text.trim()}
                onClick={() => void onSave(draft)}
              >
                {saving ? "Saving…" : "Save"}
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
            {success ? <p className="text-sm text-green-700 dark:text-green-400">{success}</p> : null}
            {canEdit ? (
              <>
                <Button type="button" size="touch" className="w-full" onClick={() => setMode("edit")}>
                  Edit
                </Button>
                <div className="flex gap-2">
                  {placed && onMovePin ? (
                    <Button
                      type="button"
                      variant="outline"
                      size="touch"
                      className="flex-1"
                      onClick={onMovePin}
                    >
                      Move pin
                    </Button>
                  ) : null}
                  {!placed && onPlaceOnImage ? (
                    <Button
                      type="button"
                      variant="outline"
                      size="touch"
                      className="flex-1"
                      onClick={onPlaceOnImage}
                    >
                      Place on image
                    </Button>
                  ) : null}
                  <Button
                    type="button"
                    variant="destructive"
                    size="touch"
                    className="flex-1"
                    onClick={onDelete}
                  >
                    Delete
                  </Button>
                </div>
              </>
            ) : (
              <Button type="button" variant="outline" size="touch" className="w-full" onClick={() => onOpenChange(false)}>
                Close
              </Button>
            )}
          </div>
        )
      }
    >
      {mode === "view" ? (
        <div className="space-y-3">
          <Badge variant="secondary">{CATEGORY_LABELS[annotation.category]}</Badge>
          <p className="text-base leading-relaxed">{annotation.text}</p>
          <AnnotationPinMeta annotation={annotation} culturalEntities={culturalEntities} />
          {placed ? (
            <p className="text-xs text-muted-foreground">
              Pin at {annotation.x_percent?.toFixed(1)}%, {annotation.y_percent?.toFixed(1)}%
            </p>
          ) : null}
        </div>
      ) : (
        <AnnotationPinForm
          values={draft}
          onChange={setDraft}
          culturalEntities={culturalEntities}
          tagSuggestions={tagSuggestions}
          noteId="annotation-detail-edit-note"
        />
      )}
    </BottomSheet>
  );
}
