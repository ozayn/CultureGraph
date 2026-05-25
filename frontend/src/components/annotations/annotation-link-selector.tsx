"use client";

import { useMemo, useState } from "react";

import { ENTITY_TYPE_LABELS } from "@/lib/entity-types";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { normalizeConceptNames } from "@/lib/annotation-suggestions";
import type { CulturalEntity } from "@/lib/types";
import { cn } from "@/lib/utils";

interface AnnotationLinkSelectorProps {
  culturalEntities: CulturalEntity[];
  linkedEntityIds: number[];
  linkedConceptNames: string[];
  onLinkedEntityIdsChange: (ids: number[]) => void;
  onLinkedConceptNamesChange: (names: string[]) => void;
}

export function AnnotationLinkSelector({
  culturalEntities,
  linkedEntityIds,
  linkedConceptNames,
  onLinkedEntityIdsChange,
  onLinkedConceptNamesChange,
}: AnnotationLinkSelectorProps) {
  const [conceptDraft, setConceptDraft] = useState("");

  const linkableEntities = useMemo(
    () =>
      culturalEntities
        .filter((entity) => entity.entity_type !== "artwork")
        .sort((left, right) => left.name.localeCompare(right.name)),
    [culturalEntities]
  );

  function toggleEntity(entityId: number) {
    if (linkedEntityIds.includes(entityId)) {
      onLinkedEntityIdsChange(linkedEntityIds.filter((id) => id !== entityId));
      return;
    }
    onLinkedEntityIdsChange([...linkedEntityIds, entityId]);
  }

  function addConceptName(raw: string) {
    const next = normalizeConceptNames([...linkedConceptNames, raw]);
    if (next.length !== linkedConceptNames.length) {
      onLinkedConceptNamesChange(next);
    }
    setConceptDraft("");
  }

  function removeConceptName(name: string) {
    onLinkedConceptNamesChange(linkedConceptNames.filter((item) => item !== name));
  }

  return (
    <div className="space-y-4">
      {linkableEntities.length > 0 ? (
        <div className="space-y-2">
          <Label>Linked entries from this visit</Label>
          <div className="flex flex-wrap gap-2">
            {linkableEntities.map((entity) => {
              const selected = linkedEntityIds.includes(entity.id);
              return (
                <button
                  key={entity.id}
                  type="button"
                  className={cn(
                    "min-h-10 rounded-full border px-3 py-1.5 text-left text-xs transition-colors",
                    selected
                      ? "border-foreground bg-foreground text-background"
                      : "border-border bg-background text-foreground active:bg-muted"
                  )}
                  onClick={() => toggleEntity(entity.id)}
                >
                  <span className="font-medium">{entity.name}</span>
                  <span
                    className={cn(
                      "ml-1.5",
                      selected ? "text-background/80" : "text-muted-foreground"
                    )}
                  >
                    · {ENTITY_TYPE_LABELS[entity.entity_type]}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      ) : null}

      <div className="space-y-2">
        <Label htmlFor="linked-concept-names">Linked concepts</Label>
        {linkedConceptNames.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {linkedConceptNames.map((name) => (
              <button
                key={name}
                type="button"
                className="min-h-9 rounded-full border border-border px-3 text-xs text-muted-foreground active:bg-muted"
                onClick={() => removeConceptName(name)}
              >
                {name} ×
              </button>
            ))}
          </div>
        ) : null}
        <Input
          id="linked-concept-names"
          value={conceptDraft}
          placeholder="Type a concept and press Enter"
          className="min-h-11"
          onChange={(event) => setConceptDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === ",") {
              event.preventDefault();
              if (conceptDraft.trim()) addConceptName(conceptDraft);
            }
          }}
          onBlur={() => {
            if (conceptDraft.trim()) addConceptName(conceptDraft);
          }}
        />
        <p className="text-xs text-muted-foreground">
          Optional links to visit entries or freeform concepts.
        </p>
      </div>
    </div>
  );
}
