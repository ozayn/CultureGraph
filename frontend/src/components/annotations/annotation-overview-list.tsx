"use client";

import { AdminActionsMenu } from "@/components/admin/admin-actions-menu";
import { AnnotationPinMeta } from "@/components/annotations/annotation-pin-meta";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CATEGORY_LABELS, type Annotation, type CulturalEntity } from "@/lib/types";

interface AnnotationOverviewListProps {
  placed: Annotation[];
  unplaced: Annotation[];
  canEdit: boolean;
  culturalEntities?: CulturalEntity[];
  onOpenDetail: (annotation: Annotation) => void;
  onDelete: (annotation: Annotation) => void;
  onPlaceOnImage?: (annotationId: number) => void;
  showPlaceOnImage?: boolean;
  placeOnImageDisabled?: boolean;
}

export function AnnotationOverviewList({
  placed,
  unplaced,
  canEdit,
  culturalEntities = [],
  onOpenDetail,
  onDelete,
  onPlaceOnImage,
  showPlaceOnImage = false,
  placeOnImageDisabled = false,
}: AnnotationOverviewListProps) {
  if (placed.length === 0 && unplaced.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
        No annotations yet.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {unplaced.length > 0 ? (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-muted-foreground">Unplaced annotations</h3>
          <ul className="space-y-3">
            {unplaced.map((annotation) => (
              <li
                key={annotation.id}
                className="rounded-xl border border-dashed border-border bg-muted/20 p-4"
              >
                <div className="flex items-start gap-2">
                  <button
                    type="button"
                    className="min-w-0 flex-1 text-left"
                    onClick={() => onOpenDetail(annotation)}
                  >
                    <div className="mb-2">
                      <Badge variant="secondary">
                        {CATEGORY_LABELS[annotation.category]}
                      </Badge>
                    </div>
                    <p className="text-base leading-relaxed">{annotation.text}</p>
                    <AnnotationPinMeta
                      annotation={annotation}
                      culturalEntities={culturalEntities}
                    />
                  </button>
                  {canEdit ? (
                    <AdminActionsMenu
                      label={`Actions for unplaced annotation ${annotation.id}`}
                      onEdit={() => onOpenDetail(annotation)}
                      onDelete={() => onDelete(annotation)}
                    />
                  ) : null}
                </div>
                {canEdit && showPlaceOnImage && onPlaceOnImage ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="mt-3 min-h-10"
                    disabled={placeOnImageDisabled}
                    onClick={() => onPlaceOnImage(annotation.id)}
                  >
                    Place on image
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {placed.length > 0 ? (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-muted-foreground">Pinned annotations</h3>
          <ul className="space-y-3">
            {placed.map((annotation, index) => (
              <li
                key={annotation.id}
                className="rounded-xl border border-border bg-card p-4"
              >
                <div className="flex items-start gap-2">
                  <button
                    type="button"
                    className="min-w-0 flex-1 text-left"
                    onClick={() => onOpenDetail(annotation)}
                  >
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <span className="inline-flex size-7 items-center justify-center rounded-full bg-muted text-xs font-medium">
                        {index + 1}
                      </span>
                      <Badge variant="secondary">
                        {CATEGORY_LABELS[annotation.category]}
                      </Badge>
                    </div>
                    <p className="text-base leading-relaxed">{annotation.text}</p>
                    <AnnotationPinMeta
                      annotation={annotation}
                      culturalEntities={culturalEntities}
                    />
                  </button>
                  {canEdit ? (
                    <AdminActionsMenu
                      label={`Actions for annotation ${index + 1}`}
                      onEdit={() => onOpenDetail(annotation)}
                      onDelete={() => onDelete(annotation)}
                    />
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
