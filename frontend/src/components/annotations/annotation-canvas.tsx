"use client";

import type { KonvaEventObject } from "konva/lib/Node";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { AnnotationDetailSheet } from "@/components/annotations/annotation-detail-sheet";
import { AnnotationOverviewList } from "@/components/annotations/annotation-overview-list";
import { AnnotationPinForm } from "@/components/annotations/annotation-pin-form";
import { PlacementDebugPanel } from "@/components/annotations/placement-debug";
import { CATEGORY_COLORS } from "@/components/annotations/konva-canvas-stage";
import { ConfirmDeleteDialog } from "@/components/admin/confirm-delete-dialog";
import { AuthGate } from "@/components/auth/auth-gate";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { Button } from "@/components/ui/button";
import {
  annotationToFormValues,
  emptyAnnotationPinFormValues,
  formValuesToAnnotationPayload,
  type AnnotationPinFormValues,
} from "@/lib/annotation-form";
import { buildAnnotationTagSuggestions } from "@/lib/annotation-suggestions";
import { isPlacedAnnotation, splitAnnotationsByPlacement } from "@/lib/annotation-placement";
import { percentFromStagePoint } from "@/lib/annotation-coordinates";
import { logAnnotationRequest } from "@/lib/annotation-debug";
import { api } from "@/lib/api";
import { emptyPlacementDebug } from "@/lib/placement-debug";
import {
  clearPendingAiAnnotation,
  consumePendingAiAnnotation,
} from "@/lib/pending-ai-annotation";
import {
  consumePendingAnnotationPlacement,
} from "@/lib/pending-annotation-placement";
import { persistAcceptedAiSuggestion } from "@/lib/persist-ai-suggestion";
import {
  suggestedAnnotationToFormValues,
  suggestionMatchKey,
} from "@/lib/research-suggestions";
import { useAuth } from "@/contexts/auth-context";
import {
  type AiSuggestedAnnotation,
  type Annotation,
  type CulturalEntity,
} from "@/lib/types";
import { cn } from "@/lib/utils";

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

function readInitialPlacement(artworkId: number, initialAnnotations: Annotation[]) {
  if (typeof window === "undefined") {
    return { pendingAi: null, placing: null, moving: null, newPinMode: true };
  }

  const pendingAi = consumePendingAiAnnotation(artworkId);
  const annotationId = consumePendingAnnotationPlacement(artworkId);
  const target = annotationId
    ? initialAnnotations.find((annotation) => annotation.id === annotationId) ?? null
    : null;

  if (target && isPlacedAnnotation(target)) {
    return {
      pendingAi,
      placing: null,
      moving: target,
      newPinMode: false,
    };
  }

  return {
    pendingAi,
    placing: target,
    moving: null,
    newPinMode: !pendingAi && !target,
  };
}

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
  const [pinFormOpen, setPinFormOpen] = useState(false);
  const [formValues, setFormValues] = useState<AnnotationPinFormValues>(
    emptyAnnotationPinFormValues()
  );
  const [placementTapDebug, setPlacementTapDebug] = useState<{
    tapX: number;
    tapY: number;
    xPercent: number;
    yPercent: number;
  } | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedAnnotation, setSelectedAnnotation] = useState<Annotation | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [deletingAnnotation, setDeletingAnnotation] = useState<Annotation | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [placementInit] = useState(() =>
    readInitialPlacement(artworkId, initialAnnotations)
  );
  const [pendingAiSuggestion, setPendingAiSuggestion] = useState<AiSuggestedAnnotation | null>(
    placementInit.pendingAi
  );
  const [placingAnnotation, setPlacingAnnotation] = useState<Annotation | null>(
    placementInit.placing
  );
  const [movingAnnotation, setMovingAnnotation] = useState<Annotation | null>(
    placementInit.moving
  );
  const [newPinMode, setNewPinMode] = useState(placementInit.newPinMode);

  const { placed: placedAnnotations, unplaced: unplacedAnnotations } = useMemo(
    () => splitAnnotationsByPlacement(annotations),
    [annotations]
  );

  const tagSuggestions = useMemo(
    () => buildAnnotationTagSuggestions(culturalEntities),
    [culturalEntities]
  );

  const moveModeActive = Boolean(movingAnnotation);
  const placementModeActive = Boolean(
    placingAnnotation || pendingAiSuggestion || newPinMode
  );
  const canvasInteractionActive = (placementModeActive || moveModeActive) && canEdit;

  const placementDebug = useMemo(() => {
    if (process.env.NODE_ENV !== "development") return null;
    return emptyPlacementDebug({
      imageWidth: image?.naturalWidth ?? 0,
      imageHeight: image?.naturalHeight ?? 0,
      stageWidth: size.width,
      stageHeight: size.height,
      tapX: placementTapDebug?.tapX ?? null,
      tapY: placementTapDebug?.tapY ?? null,
      xPercent: placementTapDebug?.xPercent ?? null,
      yPercent: placementTapDebug?.yPercent ?? null,
      suggestionKey: pendingAiSuggestion
        ? suggestionMatchKey(pendingAiSuggestion)
        : null,
    });
  }, [image, pendingAiSuggestion, placementTapDebug, size.height, size.width]);

  const refetchAnnotations = useCallback(async () => {
    const refreshed = await api.get<Annotation[]>(
      `/api/artworks/${artworkId}/annotations`
    );
    setAnnotations(refreshed);
    return refreshed;
  }, [artworkId]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !canvasInteractionActive) return;

    const preventScroll = (event: TouchEvent) => {
      if (event.touches.length === 1) {
        event.preventDefault();
      }
    };

    container.addEventListener("touchmove", preventScroll, { passive: false });
    return () => container.removeEventListener("touchmove", preventScroll);
  }, [canvasInteractionActive]);

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

  const openPinForm = useCallback(
    (
      xPercent: number | null,
      yPercent: number | null,
      prefill?: AnnotationPinFormValues
    ) => {
      if (xPercent !== null && yPercent !== null) {
        setPendingPin({
          x_percent: Number(xPercent.toFixed(2)),
          y_percent: Number(yPercent.toFixed(2)),
        });
      } else {
        setPendingPin(null);
      }
      setPinFormOpen(true);
      setFormValues(prefill ?? emptyAnnotationPinFormValues());
      setError(null);
    },
    []
  );

  function cancelPlacementMode() {
    setNewPinMode(false);
    setPendingPin(null);
    setPinFormOpen(false);
    setPlacingAnnotation(null);
    setPendingAiSuggestion(null);
    clearPendingAiAnnotation(artworkId);
    setMovingAnnotation(null);
    setError(null);
  }

  function cancelMoveMode() {
    setMovingAnnotation(null);
    setError(null);
  }

  function openAnnotationDetail(annotation: Annotation) {
    setSelectedAnnotation(annotation);
    setSuccessMessage(null);
    setError(null);
  }

  function startMovePin(annotation: Annotation) {
    setSelectedAnnotation(null);
    setMovingAnnotation(annotation);
    setNewPinMode(false);
    setPlacingAnnotation(null);
    setPendingPin(null);
    setPinFormOpen(false);
    setPendingAiSuggestion(null);
    setSuccessMessage(null);
    setError(null);
  }

  const saveAnnotationPlacement = useCallback(
    async (annotation: Annotation, xPercent: number, yPercent: number) => {
      setSaving(true);
      setError(null);
      try {
        await api.patch<Annotation>(
          `/api/artworks/${artworkId}/annotations/${annotation.id}`,
          {
            x_percent: Number(xPercent.toFixed(2)),
            y_percent: Number(yPercent.toFixed(2)),
          }
        );
        const refreshed = await refetchAnnotations();
        setPlacingAnnotation(null);
        setNewPinMode(false);
        setSuccessMessage("Pin placed on the image.");
        const updated = refreshed.find((item) => item.id === annotation.id);
        if (updated) setSelectedAnnotation(updated);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not place annotation on the image.");
      } finally {
        setSaving(false);
      }
    },
    [artworkId, refetchAnnotations]
  );

  const saveMovedPin = useCallback(
    async (annotation: Annotation, xPercent: number, yPercent: number) => {
      setSaving(true);
      setError(null);
      setSuccessMessage(null);
      try {
        await api.patch<Annotation>(
          `/api/artworks/${artworkId}/annotations/${annotation.id}`,
          {
            x_percent: Number(xPercent.toFixed(2)),
            y_percent: Number(yPercent.toFixed(2)),
          }
        );
        await refetchAnnotations();
        setMovingAnnotation(null);
        setSuccessMessage("Pin moved.");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not move pin.");
      } finally {
        setSaving(false);
      }
    },
    [artworkId, refetchAnnotations]
  );

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
      if (!canvasInteractionActive) {
        return;
      }
      if (size.width <= 0 || size.height <= 0) {
        setError("The canvas is still loading. Try again in a moment.");
        return;
      }

      const percent = percentFromStagePoint({ x, y }, size);
      if (!percent) {
        setError("Could not read tap position. Try again.");
        return;
      }

      if (process.env.NODE_ENV === "development") {
        setPlacementTapDebug({
          tapX: x,
          tapY: y,
          xPercent: percent.x_percent,
          yPercent: percent.y_percent,
        });
      }

      const { x_percent: xPercent, y_percent: yPercent } = percent;

      if (movingAnnotation) {
        void saveMovedPin(movingAnnotation, xPercent, yPercent);
        return;
      }

      if (placingAnnotation) {
        void saveAnnotationPlacement(placingAnnotation, xPercent, yPercent);
        return;
      }

      openPinForm(
        xPercent,
        yPercent,
        pendingAiSuggestion ? suggestedAnnotationToFormValues(pendingAiSuggestion) : undefined
      );
    },
    [
      authLoading,
      canEdit,
      openPinForm,
      movingAnnotation,
      pendingAiSuggestion,
      placingAnnotation,
      canvasInteractionActive,
      saveAnnotationPlacement,
      saveMovedPin,
      size,
    ]
  );

  const handlePinSelect = useCallback(
    (pinId: number) => {
      if (canvasInteractionActive) return;
      const annotation = placedAnnotations.find((item) => item.id === pinId);
      if (annotation) openAnnotationDetail(annotation);
    },
    [canvasInteractionActive, placedAnnotations]
  );

  const handleStagePointer = useCallback(
    (event: KonvaEventObject<MouseEvent | TouchEvent>) => {
      const stage = event.target.getStage();
      const pointer = stage?.getPointerPosition();
      if (!pointer) return;
      placePin(pointer.x, pointer.y);
    },
    [placePin]
  );

  const pins = useMemo(
    () =>
      placedAnnotations.map((annotation, index) => ({
        ...annotation,
        x: ((annotation.x_percent ?? 0) / 100) * size.width,
        y: ((annotation.y_percent ?? 0) / 100) * size.height,
        color: CATEGORY_COLORS[annotation.category],
        label: String(index + 1),
      })),
    [placedAnnotations, size.height, size.width]
  );

  function startPlacingAnnotation(annotation: Annotation) {
    setSelectedAnnotation(null);
    setMovingAnnotation(null);
    setPlacingAnnotation(annotation);
    setPendingPin(null);
    setPendingAiSuggestion(null);
    setNewPinMode(false);
    setError(null);
    setSuccessMessage(null);
  }

  async function saveAnnotation() {
    if (!canEdit) {
      setError(SIGN_IN_MESSAGE);
      return;
    }
    if (!pinFormOpen || !formValues.text.trim()) return;

    const endpoint = `/api/artworks/${artworkId}/annotations`;
    const payload = {
      x_percent: pendingPin?.x_percent ?? null,
      y_percent: pendingPin?.y_percent ?? null,
      ...formValuesToAnnotationPayload(formValues),
    };

    const aiSuggestion = pendingAiSuggestion;

    setSaving(true);
    setError(null);
    logAnnotationRequest(endpoint, payload);

    try {
      const created = await api.post<Annotation>(endpoint, payload);
      await refetchAnnotations();

      if (aiSuggestion) {
        try {
          await persistAcceptedAiSuggestion(artworkId, aiSuggestion, created.id);
        } catch {
          // Annotation saved; suggestion status can be fixed on research panel.
        }
      }

      setPendingPin(null);
      setPinFormOpen(false);
      setFormValues(emptyAnnotationPinFormValues());
      setPendingAiSuggestion(null);
      clearPendingAiAnnotation(artworkId);
      setNewPinMode(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save annotation.");
    } finally {
      setSaving(false);
    }
  }

  async function saveAnnotationDetail(values: AnnotationPinFormValues) {
    if (!selectedAnnotation || !values.text.trim()) return;
    setSaving(true);
    setError(null);
    setSuccessMessage(null);
    try {
      await api.patch<Annotation>(
        `/api/artworks/${artworkId}/annotations/${selectedAnnotation.id}`,
        formValuesToAnnotationPayload(values)
      );
      const refreshed = await refetchAnnotations();
      const updated = refreshed.find((item) => item.id === selectedAnnotation.id);
      if (updated) setSelectedAnnotation(updated);
      setSuccessMessage("Annotation saved.");
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
      await refetchAnnotations();
      setDeletingAnnotation(null);
      setSelectedAnnotation(null);
      setSuccessMessage("Annotation deleted.");
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
      {!canEdit && !authLoading ? <AuthGate /> : null}

      {moveModeActive && showImageCanvas ? (
        <div className="rounded-xl border border-primary/30 bg-primary/5 px-4 py-3 text-sm">
          <p className="font-medium text-foreground">Move pin</p>
          <p className="mt-1 text-muted-foreground">{movingAnnotation?.text}</p>
          <p className="mt-2 text-xs text-muted-foreground">
            Tap the image where the pin should go. The new position saves immediately.
          </p>
          <Button
            type="button"
            variant="outline"
            size="touch"
            className="mt-3"
            onClick={cancelMoveMode}
          >
            Cancel
          </Button>
        </div>
      ) : null}

      {placementModeActive && showImageCanvas && !moveModeActive ? (
        <div className="rounded-xl border border-primary/30 bg-primary/5 px-4 py-3 text-sm">
          <p className="font-medium text-foreground">Tap image to place pin</p>
          {placingAnnotation ? (
            <p className="mt-1 text-muted-foreground">{placingAnnotation.text}</p>
          ) : null}
          {pendingAiSuggestion ? (
            <p className="mt-1 text-muted-foreground">{pendingAiSuggestion.note}</p>
          ) : null}
          <p className="mt-2 text-xs text-muted-foreground">
            Tap anywhere on the artwork. Taps on existing pins are ignored.
          </p>
          <Button
            type="button"
            variant="outline"
            size="touch"
            className="mt-3"
            onClick={cancelPlacementMode}
          >
            Cancel placement
          </Button>
        </div>
      ) : null}

      {successMessage && !pinFormOpen && !selectedAnnotation ? (
        <p className="text-sm text-green-700 dark:text-green-400">{successMessage}</p>
      ) : null}

      <p className="text-base text-muted-foreground">
        {authLoading
          ? "Checking sign-in status…"
          : canEdit
            ? showImageCanvas
              ? canvasInteractionActive
                ? moveModeActive
                  ? "Tap the image to move this pin."
                  : "Tap the image to place a pin at that spot."
                : "Tap a pin to view details, or add a new pin below."
              : "Add an image before placing pins, or add a text-only observation below."
            : SIGN_IN_MESSAGE}
      </p>

      {process.env.NODE_ENV === "development" && canvasInteractionActive ? (
        <PlacementDebugPanel state={placementDebug} />
      ) : null}

      {error && !pinFormOpen && !selectedAnnotation ? (
        <p className="text-sm text-destructive">{error}</p>
      ) : null}

      <div
        ref={containerRef}
        className={cn(
          "w-full overflow-hidden rounded-xl border border-border bg-[#f3efe8]",
          canvasInteractionActive && "touch-none",
          showImageCanvas && canEdit && !canvasInteractionActive && "opacity-90"
        )}
      >
        {showImageCanvas && canvasReady ? (
          <KonvaCanvasStage
            width={size.width}
            height={size.height}
            image={activeImage}
            pins={pins}
            pendingPin={pendingPin}
            canvasInteractionActive={canvasInteractionActive}
            highlightedPinId={movingAnnotation?.id ?? selectedAnnotation?.id ?? null}
            onPinSelect={handlePinSelect}
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
                onClick={() => openPinForm(null, null)}
              >
                Add text-only observation
              </Button>
            ) : null}
          </div>
        )}
      </div>

      <AnnotationOverviewList
        placed={placedAnnotations}
        unplaced={unplacedAnnotations}
        canEdit={canEdit}
        culturalEntities={culturalEntities}
        onOpenDetail={openAnnotationDetail}
        onDelete={setDeletingAnnotation}
        onPlaceOnImage={(annotationId) => {
          const annotation = annotations.find((item) => item.id === annotationId);
          if (annotation) startPlacingAnnotation(annotation);
        }}
        showPlaceOnImage={canEdit && showImageCanvas}
        placeOnImageDisabled={saving}
      />

      <BottomSheet
        open={pinFormOpen}
        onOpenChange={(open) => {
          if (!open) {
            setPinFormOpen(false);
            setPendingPin(null);
          }
        }}
        title={pendingPin ? "New annotation" : "Text-only annotation"}
        description={
          pendingPin
            ? "What did you notice at this spot?"
            : "Save without a pin, or place it on the image later."
        }
        footer={
          <>
            {error ? <p className="mb-3 text-sm text-destructive">{error}</p> : null}
            <Button
              type="button"
              size="touch"
              className="w-full"
              onClick={() => void saveAnnotation()}
              disabled={saving || !formValues.text.trim() || !canEdit}
            >
              {saving ? "Saving…" : pendingPin ? "Save pin" : "Save annotation"}
            </Button>
          </>
        }
      >
        <AnnotationPinForm
          values={formValues}
          onChange={setFormValues}
          culturalEntities={culturalEntities}
          tagSuggestions={tagSuggestions}
        />
      </BottomSheet>

      <AnnotationDetailSheet
        annotation={selectedAnnotation}
        open={selectedAnnotation !== null}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedAnnotation(null);
            setSuccessMessage(null);
            setError(null);
          }
        }}
        canEdit={canEdit}
        culturalEntities={culturalEntities}
        tagSuggestions={tagSuggestions}
        saving={saving}
        error={error}
        success={successMessage}
        onSave={saveAnnotationDetail}
        onDelete={() => {
          if (selectedAnnotation) setDeletingAnnotation(selectedAnnotation);
        }}
        onMovePin={
          selectedAnnotation && isPlacedAnnotation(selectedAnnotation)
            ? () => startMovePin(selectedAnnotation)
            : undefined
        }
        onPlaceOnImage={
          selectedAnnotation && !isPlacedAnnotation(selectedAnnotation)
            ? () => startPlacingAnnotation(selectedAnnotation)
            : undefined
        }
      />

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
