"use client";

import { Badge } from "@/components/ui/badge";
import { resolveLinkedEntityLabels } from "@/lib/annotation-form";
import type { Annotation, CulturalEntity } from "@/lib/types";

interface AnnotationPinMetaProps {
  annotation: Annotation;
  culturalEntities?: CulturalEntity[];
}

export function AnnotationPinMeta({
  annotation,
  culturalEntities = [],
}: AnnotationPinMetaProps) {
  const tags = annotation.tags ?? [];
  const linkedEntityLabels = resolveLinkedEntityLabels(
    annotation.linked_entity_ids ?? [],
    culturalEntities
  );
  const linkedConceptNames = annotation.linked_concept_names ?? [];
  const links = [...linkedEntityLabels, ...linkedConceptNames];

  if (tags.length === 0 && links.length === 0) {
    return null;
  }

  return (
    <div className="mt-3 space-y-2">
      {tags.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {tags.map((tag) => (
            <Badge key={tag} variant="outline" className="text-[11px] font-normal">
              {tag}
            </Badge>
          ))}
        </div>
      ) : null}
      {links.length > 0 ? (
        <p className="text-xs leading-relaxed text-muted-foreground">
          Linked: {links.join(" · ")}
        </p>
      ) : null}
    </div>
  );
}
