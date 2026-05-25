"use client";

import { AnnotationLinkSelector } from "@/components/annotations/annotation-link-selector";
import { TagInput } from "@/components/annotations/tag-input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { AnnotationPinFormValues } from "@/lib/annotation-form";
import {
  ANNOTATION_CATEGORIES,
  CATEGORY_LABELS,
  type CulturalEntity,
} from "@/lib/types";
import { cn } from "@/lib/utils";

interface AnnotationPinFormProps {
  values: AnnotationPinFormValues;
  onChange: (values: AnnotationPinFormValues) => void;
  culturalEntities: CulturalEntity[];
  tagSuggestions: string[];
  noteId?: string;
}

export function AnnotationPinForm({
  values,
  onChange,
  culturalEntities,
  tagSuggestions,
  noteId = "annotation-note",
}: AnnotationPinFormProps) {
  function patch(partial: Partial<AnnotationPinFormValues>) {
    onChange({ ...values, ...partial });
  }

  return (
    <div className="space-y-4 pb-2">
      <div className="space-y-2">
        <Label>Category</Label>
        <div className="flex flex-wrap gap-2">
          {ANNOTATION_CATEGORIES.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => patch({ category: item })}
              className={cn(
                "min-h-11 rounded-full border px-4 py-2 text-sm transition-colors",
                values.category === item
                  ? "border-foreground bg-foreground text-background"
                  : "border-border bg-background text-foreground active:bg-muted"
              )}
            >
              {CATEGORY_LABELS[item]}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor={noteId}>Note</Label>
        <Textarea
          id={noteId}
          rows={4}
          value={values.text}
          onChange={(event) => patch({ text: event.target.value })}
          placeholder="What did you notice here?"
        />
      </div>

      <TagInput
        value={values.tags}
        onChange={(tags) => patch({ tags })}
        suggestions={tagSuggestions}
      />

      <AnnotationLinkSelector
        culturalEntities={culturalEntities}
        linkedEntityIds={values.linkedEntityIds}
        linkedConceptNames={values.linkedConceptNames}
        onLinkedEntityIdsChange={(linkedEntityIds) => patch({ linkedEntityIds })}
        onLinkedConceptNamesChange={(linkedConceptNames) =>
          patch({ linkedConceptNames })
        }
      />
    </div>
  );
}
