import type { Annotation, AnnotationCategory, CulturalEntity } from "@/lib/types";
import {
  normalizeAnnotationTags,
  normalizeConceptNames,
} from "@/lib/annotation-suggestions";

export interface AnnotationPinFormValues {
  category: AnnotationCategory;
  text: string;
  tags: string[];
  linkedEntityIds: number[];
  linkedConceptNames: string[];
}

export function emptyAnnotationPinFormValues(
  category: AnnotationCategory = "observation"
): AnnotationPinFormValues {
  return {
    category,
    text: "",
    tags: [],
    linkedEntityIds: [],
    linkedConceptNames: [],
  };
}

export function annotationToFormValues(annotation: Annotation): AnnotationPinFormValues {
  return {
    category: annotation.category,
    text: annotation.text,
    tags: annotation.tags ?? [],
    linkedEntityIds: annotation.linked_entity_ids ?? [],
    linkedConceptNames: annotation.linked_concept_names ?? [],
  };
}

export function formValuesToAnnotationPayload(values: AnnotationPinFormValues) {
  return {
    category: values.category,
    text: values.text.trim(),
    tags: normalizeAnnotationTags(values.tags),
    linked_entity_ids: values.linkedEntityIds,
    linked_concept_names: normalizeConceptNames(values.linkedConceptNames),
  };
}

export function resolveLinkedEntityLabels(
  linkedEntityIds: number[],
  culturalEntities: CulturalEntity[]
): string[] {
  const byId = new Map(culturalEntities.map((entity) => [entity.id, entity.name]));
  return linkedEntityIds
    .map((id) => byId.get(id))
    .filter((name): name is string => Boolean(name));
}
