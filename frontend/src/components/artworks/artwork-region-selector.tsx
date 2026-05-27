"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { mediaUrl } from "@/lib/api";
import {
  clampArtworkRegion,
  DEFAULT_ARTWORK_REGION,
  type ArtworkImageRegion,
} from "@/lib/artwork-region";
import { cn } from "@/lib/utils";

interface ArtworkRegionSelectorProps {
  imageUrl: string;
  initialRegion?: ArtworkImageRegion | null;
  saving?: boolean;
  onSave: (region: ArtworkImageRegion) => void;
  onUseFullImage: () => void;
  onSkip: () => void;
}

type DragMode = "move" | "resize";

interface DragState {
  mode: DragMode;
  pointerId: number;
  startX: number;
  startY: number;
  startRegion: ArtworkImageRegion;
}

export function ArtworkRegionSelector({
  imageUrl,
  initialRegion,
  saving = false,
  onSave,
  onUseFullImage,
  onSkip,
}: ArtworkRegionSelectorProps) {
  const [region, setRegion] = useState<ArtworkImageRegion>(
    initialRegion ?? DEFAULT_ARTWORK_REGION
  );
  const dragRef = useRef<DragState | null>(null);
  const frameRef = useRef<HTMLDivElement | null>(null);

  const resolvedUrl = mediaUrl(imageUrl);

  const updateRegion = useCallback((next: ArtworkImageRegion) => {
    setRegion(clampArtworkRegion(next));
  }, []);

  useEffect(() => {
    function onPointerMove(event: PointerEvent) {
      const drag = dragRef.current;
      const frame = frameRef.current;
      if (!drag || !frame) return;

      const rect = frame.getBoundingClientRect();
      if (!rect.width || !rect.height) return;

      const dx = ((event.clientX - drag.startX) / rect.width) * 100;
      const dy = ((event.clientY - drag.startY) / rect.height) * 100;

      if (drag.mode === "move") {
        updateRegion({
          x_percent: drag.startRegion.x_percent + dx,
          y_percent: drag.startRegion.y_percent + dy,
          width_percent: drag.startRegion.width_percent,
          height_percent: drag.startRegion.height_percent,
        });
        return;
      }

      updateRegion({
        x_percent: drag.startRegion.x_percent,
        y_percent: drag.startRegion.y_percent,
        width_percent: drag.startRegion.width_percent + dx,
        height_percent: drag.startRegion.height_percent + dy,
      });
    }

    function onPointerUp(event: PointerEvent) {
      const drag = dragRef.current;
      if (!drag || drag.pointerId !== event.pointerId) return;
      dragRef.current = null;
    }

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    window.addEventListener("pointercancel", onPointerUp);
    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      window.removeEventListener("pointercancel", onPointerUp);
    };
  }, [updateRegion]);

  function startDrag(mode: DragMode, event: React.PointerEvent) {
    event.preventDefault();
    event.stopPropagation();
    dragRef.current = {
      mode,
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      startRegion: region,
    };
  }

  if (!resolvedUrl) {
    return <p className="text-sm text-muted-foreground">No image available.</p>;
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Drag the box to frame the artwork. Pinch-to-zoom can come later — this sets the
        area used for thumbnails and AI research.
      </p>

      <div ref={frameRef} className="relative mx-auto w-full max-w-lg touch-none select-none">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={resolvedUrl}
          alt="Select artwork region"
          className="block max-h-[55vh] w-full rounded-lg bg-muted object-contain"
          draggable={false}
        />
        <div className="pointer-events-none absolute inset-0 rounded-lg bg-black/35" />
        <div
          className="absolute border-2 border-primary bg-primary/10 shadow-[0_0_0_9999px_rgba(0,0,0,0.35)]"
          style={{
            left: `${region.x_percent}%`,
            top: `${region.y_percent}%`,
            width: `${region.width_percent}%`,
            height: `${region.height_percent}%`,
          }}
        >
          <button
            type="button"
            aria-label="Move artwork region"
            className="pointer-events-auto absolute inset-0 cursor-move"
            onPointerDown={(event) => startDrag("move", event)}
          />
          <button
            type="button"
            aria-label="Resize artwork region"
            className={cn(
              "pointer-events-auto absolute -bottom-3 -right-3 size-10 rounded-full",
              "border-2 border-primary bg-background shadow-md"
            )}
            onPointerDown={(event) => startDrag("resize", event)}
          />
        </div>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
        <Button
          type="button"
          size="touch"
          className="flex-1"
          disabled={saving}
          onClick={() => onSave(region)}
        >
          {saving ? "Saving…" : "Save selected area"}
        </Button>
        <Button
          type="button"
          size="touch"
          variant="secondary"
          className="flex-1"
          disabled={saving}
          onClick={onUseFullImage}
        >
          Use full image
        </Button>
        <Button
          type="button"
          size="touch"
          variant="outline"
          className="flex-1"
          disabled={saving}
          onClick={onSkip}
        >
          Skip for now
        </Button>
      </div>
    </div>
  );
}
