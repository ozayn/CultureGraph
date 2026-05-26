import type { Annotation } from "@/lib/types";

export type AnnotationPlacementStatus = "placed" | "unplaced";

export function isPlacedAnnotation(annotation: Pick<Annotation, "x_percent" | "y_percent">): boolean {
  return annotation.x_percent !== null && annotation.y_percent !== null;
}

export function isUnplacedAnnotation(
  annotation: Pick<Annotation, "x_percent" | "y_percent">
): boolean {
  return annotation.x_percent === null && annotation.y_percent === null;
}

export function annotationPlacementStatus(
  annotation: Pick<Annotation, "x_percent" | "y_percent">
): AnnotationPlacementStatus {
  return isPlacedAnnotation(annotation) ? "placed" : "unplaced";
}

export function splitAnnotationsByPlacement(annotations: Annotation[]) {
  const placed: Annotation[] = [];
  const unplaced: Annotation[] = [];

  for (const annotation of annotations) {
    if (isPlacedAnnotation(annotation)) {
      placed.push(annotation);
    } else {
      unplaced.push(annotation);
    }
  }

  return { placed, unplaced };
}
