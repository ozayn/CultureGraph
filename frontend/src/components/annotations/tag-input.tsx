"use client";

import { X } from "lucide-react";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { normalizeAnnotationTags } from "@/lib/annotation-suggestions";
import { cn } from "@/lib/utils";

interface TagInputProps {
  id?: string;
  label?: string;
  value: string[];
  onChange: (tags: string[]) => void;
  suggestions?: string[];
  placeholder?: string;
}

export function TagInput({
  id = "annotation-tags",
  label = "Tags",
  value,
  onChange,
  suggestions = [],
  placeholder = "Add a tag and press Enter",
}: TagInputProps) {
  const [draft, setDraft] = useState("");

  const availableSuggestions = useMemo(() => {
    const selected = new Set(value.map((tag) => tag.toLowerCase()));
    return suggestions.filter((tag) => !selected.has(tag.toLowerCase())).slice(0, 12);
  }, [suggestions, value]);

  function addTag(raw: string) {
    const next = normalizeAnnotationTags([...value, raw]);
    if (next.length !== value.length) {
      onChange(next);
    }
    setDraft("");
  }

  function removeTag(tag: string) {
    onChange(value.filter((item) => item !== tag));
  }

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      {value.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {value.map((tag) => (
            <Badge key={tag} variant="secondary" className="gap-1 pr-1">
              {tag}
              <button
                type="button"
                className="inline-flex size-6 items-center justify-center rounded-full hover:bg-muted"
                aria-label={`Remove tag ${tag}`}
                onClick={() => removeTag(tag)}
              >
                <X className="size-3.5" strokeWidth={1.75} />
              </button>
            </Badge>
          ))}
        </div>
      ) : null}
      <Input
        id={id}
        value={draft}
        placeholder={placeholder}
        className="min-h-11"
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === ",") {
            event.preventDefault();
            if (draft.trim()) addTag(draft);
          }
          if (event.key === "Backspace" && !draft && value.length > 0) {
            onChange(value.slice(0, -1));
          }
        }}
        onBlur={() => {
          if (draft.trim()) addTag(draft);
        }}
      />
      {availableSuggestions.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {availableSuggestions.map((tag) => (
            <button
              key={tag}
              type="button"
              className={cn(
                "min-h-9 rounded-full border border-border px-3 text-xs text-muted-foreground",
                "transition-colors active:bg-muted"
              )}
              onClick={() => addTag(tag)}
            >
              {tag}
            </button>
          ))}
        </div>
      ) : null}
      <p className="text-xs text-muted-foreground">Optional. Tap a suggestion or type your own.</p>
    </div>
  );
}
