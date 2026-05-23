"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { BottomSheet } from "@/components/ui/bottom-sheet";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  ANNOTATION_CATEGORIES,
  CATEGORY_LABELS,
  type Annotation,
  type AnnotationCategory,
} from "@/lib/types";

const Stage = dynamic(() => import("react-konva").then((mod) => mod.Stage), {
  ssr: false,
});
const Layer = dynamic(() => import("react-konva").then((mod) => mod.Layer), {
  ssr: false,
});
const Group = dynamic(() => import("react-konva").then((mod) => mod.Group), {
  ssr: false,
});
const Circle = dynamic(() => import("react-konva").then((mod) => mod.Circle), {
  ssr: false,
});
const Text = dynamic(() => import("react-konva").then((mod) => mod.Text), {
  ssr: false,
});
const KonvaImage = dynamic(
  () => import("react-konva").then((mod) => mod.Image),
  { ssr: false }
);

const PIN_RADIUS = 14;
const HIT_RADIUS = 22;

interface AnnotationCanvasProps {
  artworkId: number;
  imageUrl: string | null;
  initialAnnotations: Annotation[];
}

interface PendingPin {
  x_percent: number;
  y_percent: number;
}

const CATEGORY_COLORS: Record<AnnotationCategory, string> = {
  observation: "#5c4d3c",
  symbol: "#7a5c2e",
  history: "#4a5d4a",
  question: "#5a4a6a",
  composition: "#3d4a5c",
};

export function AnnotationCanvas({
  artworkId,
  imageUrl,
  initialAnnotations,
}: AnnotationCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [annotations, setAnnotations] = useState(initialAnnotations);
  const [size, setSize] = useState({ width: 320, height: 240 });
  const [image, setImage] = useState<HTMLImageElement | null>(null);
  const [pendingPin, setPendingPin] = useState<PendingPin | null>(null);
  const [category, setCategory] = useState<AnnotationCategory>("observation");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
    if (!imageUrl) return;

    const img = new window.Image();
    img.crossOrigin = "anonymous";
    img.src = imageUrl;
    img.onload = () => setImage(img);

    return () => {
      img.onload = null;
    };
  }, [imageUrl]);

  const displayImage = imageUrl ? image : null;

  const placePin = useCallback(
    (x: number, y: number) => {
      setPendingPin({
        x_percent: Number(((x / size.width) * 100).toFixed(2)),
        y_percent: Number(((y / size.height) * 100).toFixed(2)),
      });
      setNote("");
      setCategory("observation");
      setError(null);
    },
    [size.height, size.width]
  );

  const handleStageTap = useCallback(
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
    if (!pendingPin || !note.trim()) return;
    setSaving(true);
    setError(null);

    try {
      const created = await api.post<Annotation>(
        `/api/artworks/${artworkId}/annotations`,
        {
          ...pendingPin,
          category,
          text: note.trim(),
        }
      );
      setAnnotations((current) => [...current, created]);
      setPendingPin(null);
      setNote("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save annotation.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-5">
      <p className="text-base text-muted-foreground">
        Tap the image to place a pin. Pins save as percentage coordinates.
      </p>

      <div
        ref={containerRef}
        className="w-full overflow-hidden rounded-xl border border-border bg-[#f3efe8] touch-none"
      >
        {imageUrl ? (
          <Stage width={size.width} height={size.height} onTap={handleStageTap}>
            <Layer>
              {displayImage ? (
                <KonvaImage
                  image={displayImage}
                  width={size.width}
                  height={size.height}
                />
              ) : null}
              {pins.map((pin) => (
                <PinMarker key={pin.id} pin={pin} />
              ))}
              {pendingPin ? (
                <Circle
                  x={(pendingPin.x_percent / 100) * size.width}
                  y={(pendingPin.y_percent / 100) * size.height}
                  radius={PIN_RADIUS}
                  fill="#1f1a17"
                  stroke="#faf7f2"
                  strokeWidth={3}
                />
              ) : null}
            </Layer>
          </Stage>
        ) : (
          <button
            type="button"
            className="flex w-full items-center justify-center bg-[#f3efe8] px-4 text-base text-muted-foreground"
            style={{ height: size.height }}
            onClick={(event) => {
              const rect = event.currentTarget.getBoundingClientRect();
              placePin(
                event.clientX - rect.left,
                event.clientY - rect.top
              );
            }}
          >
            Tap to place a pin on this placeholder canvas
          </button>
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
              <div className="mb-2 flex items-center gap-2">
                <span className="inline-flex size-7 items-center justify-center rounded-full bg-muted text-xs font-medium">
                  {index + 1}
                </span>
                <Badge variant="secondary">
                  {CATEGORY_LABELS[annotation.category]}
                </Badge>
              </div>
              <p className="text-base leading-relaxed">{annotation.text}</p>
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
        <div className="space-y-4 pb-2">
          <div className="space-y-2">
            <Label>Category</Label>
            <div className="flex flex-wrap gap-2">
              {ANNOTATION_CATEGORIES.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setCategory(item)}
                  className={cn(
                    "min-h-11 rounded-full border px-4 py-2 text-sm transition-colors",
                    category === item
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
            <Label htmlFor="annotation-note">Note</Label>
            <Textarea
              id="annotation-note"
              rows={4}
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="What did you notice here?"
            />
          </div>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <Button
            size="touch"
            className="w-full"
            onClick={saveAnnotation}
            disabled={saving || !note.trim()}
          >
            {saving ? "Saving…" : "Save pin"}
          </Button>
        </div>
      </BottomSheet>
    </div>
  );
}

function PinMarker({
  pin,
}: {
  pin: Annotation & { x: number; y: number; color: string; label: string };
}) {
  return (
    <Group x={pin.x} y={pin.y}>
      <Circle radius={HIT_RADIUS} fill="rgba(0,0,0,0.001)" />
      <Circle
        radius={PIN_RADIUS}
        fill={pin.color}
        stroke="#faf7f2"
        strokeWidth={3}
      />
      <Text
        x={PIN_RADIUS + 6}
        y={-8}
        text={pin.label}
        fontSize={14}
        fontStyle="600"
        fill={pin.color}
      />
    </Group>
  );
}
