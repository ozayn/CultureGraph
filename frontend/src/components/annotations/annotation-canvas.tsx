"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { AnnotationPinForm } from "@/components/annotations/annotation-pin-form";
import { AnnotationPinMeta } from "@/components/annotations/annotation-pin-meta";
import { CATEGORY_COLORS } from "@/components/annotations/konva-canvas-stage";
import { AdminActionsMenu } from "@/components/admin/admin-actions-menu";
import { ConfirmDeleteDialog } from "@/components/admin/confirm-delete-dialog";
import { SignInPrompt } from "@/components/auth/sign-in-prompt";
import { Badge } from "@/components/ui/badge";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { Button } from "@/components/ui/button";
import {
  annotationToFormValues,
  emptyAnnotationPinFormValues,
  formValuesToAnnotationPayload,
  type AnnotationPinFormValues,
} from "@/lib/annotation-form";
import { buildAnnotationTagSuggestions } from "@/lib/annotation-suggestions";
import { logAnnotationRequest } from "@/lib/annotation-debug";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import { CATEGORY_LABELS, type Annotation, type CulturalEntity } from "@/lib/types";

const KonvaCanvasStage = dynamic(() => import("@/components/annotations/konva-canvas-stage"), {
  ssr: false,
  loading: () => (
    <div className="flex min-h-[240px] w-full items-center justify-center bg-[#f3efe8] text-sm text-muted-foreground">
      Loading canvas…
    </div>
  ),
});

interface AnnotationCanvasProps {
  artworkId: number;
  imageUrl: string | null;
  initialAnnotations: Annotation[];
  culturalEntities?: CulturalEntity[];
}

interface PendingPin {
  x_percent: number;
  y_percent: number;
}

const SIGN_IN_MESSAGE = "Sign in to add annotations.";

export function AnnotationCanvas({
  artworkId,
  imageUrl,
  initialAnnotations,
  culturalEntities = [],
}: AnnotationCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { canEdit, loading: authLoading } = useAuth();
  const [annotations, setAnnotations] = useState(initialAnnotations);
  const [size, setSize] = useState({ width: 320, height: 240 });
  const [image, setImage] = useState<HTMLImageElement | null>(null);
  const [imageLoadFailed, setImageLoadFailed] = useState(false);
  const [pendingPin, setPendingPin] = useState<PendingPin | null>(null);
  const [formValues, setFormValues] = useState<AnnotationPinFormValues>(
    emptyAnnotationPinFormValues()
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingAnnotation, setEditingAnnotation] = useState<Annotation | null>(null);
  const [deletingAnnotation, setDeletingAnnotation] = useState<Annotation | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const tagSuggestions = useMemo(
    () => buildAnnotationTagSuggestions(culturalEntities),
    [culturalEntities]
  );

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const updateSize = () => {
      const width = container.clientWidth;
      const aspect = image ? image.height / image.width : 4 / 3;
      setSize({ width, height: Math.round(width * aspect) });
    };

    updateSize();
    const observer = new ResizeObserver(updateSize);
    observer.observe(container);
    window.addEventListener("resize", updateSize);

    return () => {
      observer.disconnect();
      window.removeEventListener("resize", updateSize);
    };
  }, [image]);

  useEffect(() => {
    const src = imageUrl;
    if (!src) return;

    let cancelled = false;
    const resolvedSrc = src;

    function loadImage(useCrossOrigin: boolean) {
      const img = new window.Image();
      if (useCrossOrigin) {
        img.crossOrigin = "anonymous";
      }
      img.src = resolvedSrc;
      img.onload = () => {
        if (!cancelled) {
          setImage(img);
          setImageLoadFailed(false);
        }
      };
      img.onerror = () => {
        if (cancelled) return;
        if (useCrossOrigin) {
          loadImage(false);
          return;
        }
        setImage(null);
        setImageLoadFailed(true);
      };
    }

    loadImage(true);

    return () => {
      cancelled = true;
    };
  }, [imageUrl]);

  const openPinForm = useCallback((xPercent: number, yPercent: number) => {
    setPendingPin({
      x_percent: Number(xPercent.toFixed(2)),
      y_percent: Number(yPercent.toFixed(2)),
    });
    setFormValues(emptyAnnotationPinFormValues());
    setError(null);
  }, []);

  const placePin = useCallback(
    (x: number, y: number) => {
      if (authLoading) {
        setError("Checking sign-in status…");
        return;
      }
      if (!canEdit) {
        setError(SIGN_IN_MESSAGE);
        return;
      }
      if (size.width <= 0 || size.height <= 0) {
        setError("The canvas is still loading. Try again in a moment.");
        return;
      }

      openPinForm((x / size.width) * 100, (y / size.height) * 100);
    },
    [authLoading, canEdit, openPinForm, size.height, size.width]
  );

  const handleStagePointer = useCallback(
    (event: {
      target: {
        getStage: () => {
          getPointerPosition: () => { x: number; y: number } | null;
        } | null;
      };
    }) => {
      const stage = event.target.getStage();
      const pointer = stage?.getPointerPosition();
      if (!pointer) return;
      placePin(pointer.x, pointer.y);
    },
    [placePin]
  );

  const pins = useMemo(
    () =>
      annotations.map((annotation, index) => ({
        ...annotation,
        x: (annotation.x_percent / 100) * size.width,
        y: (annotation.y_percent / 100) * size.height,
        color: CATEGORY_COLORS[annotation.category],
        label: String(index + 1),
      })),
    [annotations, size.height, size.width]
  );

  async function saveAnnotation() {
    if (!canEdit) {
      setError(SIGN_IN_MESSAGE);
      return;
    }
    if (!pendingPin || !formValues.text.trim()) return;

    const endpoint = `/api/artworks/${artworkId}/annotations`;
    const payload = {
      ...pendingPin,
      ...formValuesToAnnotationPayload(formValues),
    };

    setSaving(true);
    setError(null);
    logAnnotationRequest(endpoint, payload);

    try {
      const created = await api.post<Annotation>(endpoint, payload);
      setAnnotations((current) => [...current, created]);
      setPendingPin(null);
      setFormValues(emptyAnnotationPinFormValues());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save annotation.");
    } finally {
      setSaving(false);
    }
  }

  function openAnnotationEditor(annotation: Annotation) {
    setEditingAnnotation(annotation);
    setFormValues(annotationToFormValues(annotation));
    setError(null);
  }

  async function saveAnnotationEdit() {
    if (!editingAnnotation || !formValues.text.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await api.patch<Annotation>(
        `/api/artworks/${artworkId}/annotations/${editingAnnotation.id}`,
        formValuesToAnnotationPayload(formValues)
      );
      setAnnotations((current) =>
        current.map((item) => (item.id === updated.id ? updated : item))
      );
      setEditingAnnotation(null);
      setFormValues(emptyAnnotationPinFormValues());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save annotation.");
    } finally {
      setSaving(false);
    }
  }

  async function deleteAnnotation() {
    if (!deletingAnnotation) return;
    setDeleteLoading(true);
    setError(null);
    try {
      await api.delete(
        `/api/artworks/${artworkId}/annotations/${deletingAnnotation.id}`
      );
      setAnnotations((current) =>
        current.filter((item) => item.id !== deletingAnnotation.id)
      );
      setDeletingAnnotation(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete annotation.");
    } finally {
      setDeleteLoading(false);
    }
  }

  const canvasReady = size.width > 0 && size.height > 0;
  const activeImage = imageUrl ? image : null;
  const activeImageLoadFailed = imageUrl ? imageLoadFailed : false;
  const showImageCanvas = Boolean(imageUrl) && !activeImageLoadFailed;

  return (
    <div className="space-y-5">
      {!canEdit && !authLoading ? <SignInPrompt compact /> : null}

      <p className="text-base text-muted-foreground">
        {authLoading
          ? "Checking sign-in status…"
          : canEdit
            ? showImageCanvas
              ? "Click or tap the image to place a pin. Pins save as percentage coordinates."
              : "Add an image before placing pins, or add a text-only observation below."
            : SIGN_IN_MESSAGE}
      </p>

      {error && !pendingPin && !editingAnnotation ? (
        <p className="text-sm text-destructive">{error}</p>
      ) : null}

      <div
        ref={containerRef}
        className="w-full overflow-hidden rounded-xl border border-border bg-[#f3efe8] touch-none"
      >
        {showImageCanvas && canvasReady ? (
          <KonvaCanvasStage
            width={size.width}
            height={size.height}
            image={activeImage}
            pins={pins}
            pendingPin={pendingPin}
            onStagePointer={handleStagePointer}
          />
        ) : (
          <div
            className="flex flex-col items-center justify-center gap-4 px-4 text-center text-base text-muted-foreground"
            style={{ minHeight: size.height }}
          >
            <p>
              {activeImageLoadFailed
                ? "This artwork image could not be loaded for pinning."
                : "Add an image before placing pins."}
            </p>
            {canEdit ? (
              <Button
                type="button"
                variant="outline"
                size="touch"
                onClick={() => openPinForm(50, 50)}
              >
                Add text-only observation
              </Button>
            ) : null}
          </div>
        )}
      </div>

      <ul className="space-y-3">
        {annotations.length === 0 ? (
          <li className="rounded-xl border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
            No annotations yet.
          </li>
        ) : (
          annotations.map((annotation, index) => (
            <li
              key={annotation.id}
              className="rounded-xl border border-border bg-card p-4"
            >
              <div className="mb-2 flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="inline-flex size-7 items-center justify-center rounded-full bg-muted text-xs font-medium">
                    {index + 1}
                  </span>
                  <Badge variant="secondary">
                    {CATEGORY_LABELS[annotation.category]}
                  </Badge>
                </div>
                {canEdit ? (
                  <AdminActionsMenu
                    label={`Actions for annotation ${index + 1}`}
                    onEdit={() => openAnnotationEditor(annotation)}
                    onDelete={() => setDeletingAnnotation(annotation)}
                  />
                ) : null}
              </div>
              <p className="text-base leading-relaxed">{annotation.text}</p>
              <AnnotationPinMeta
                annotation={annotation}
                culturalEntities={culturalEntities}
              />
            </li>
          ))
        )}
      </ul>

      <BottomSheet
        open={pendingPin !== null}
        onOpenChange={(open) => {
          if (!open) setPendingPin(null);
        }}
        title="New annotation"
        description="What did you notice at this spot?"
      >
        <AnnotationPinForm
          values={formValues}
          onChange={setFormValues}
          culturalEntities={culturalEntities}
          tagSuggestions={tagSuggestions}
        />
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        <Button
          type="button"
          size="touch"
          className="mt-4 w-full"
          onClick={() => void saveAnnotation()}
          disabled={saving || !formValues.text.trim() || !canEdit}
        >
          {saving ? "Saving…" : "Save pin"}
        </Button>
      </BottomSheet>

      <BottomSheet
        open={editingAnnotation !== null}
        onOpenChange={(open) => {
          if (!open) setEditingAnnotation(null);
        }}
        title="Edit annotation"
        description="Update category, note, tags, or links."
      >
        <AnnotationPinForm
          values={formValues}
          onChange={setFormValues}
          culturalEntities={culturalEntities}
          tagSuggestions={tagSuggestions}
          noteId="edit-annotation-note"
        />
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        <Button
          type="button"
          size="touch"
          className="mt-4 w-full"
          onClick={() => void saveAnnotationEdit()}
          disabled={saving || !formValues.text.trim() || !canEdit}
        >
          {saving ? "Saving…" : "Save changes"}
        </Button>
      </BottomSheet>

      <ConfirmDeleteDialog
        open={deletingAnnotation !== null}
        onOpenChange={(open) => {
          if (!open) setDeletingAnnotation(null);
        }}
        title="Delete annotation?"
        description="This pin and its note will be removed permanently."
        loading={deleteLoading}
        onConfirm={deleteAnnotation}
      />
    </div>
  );
}
