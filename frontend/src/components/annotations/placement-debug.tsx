"use client";

import type { PlacementDebugState } from "@/lib/placement-debug";

interface PlacementDebugPanelProps {
  state: PlacementDebugState | null;
}

export function PlacementDebugPanel({ state }: PlacementDebugPanelProps) {
  if (process.env.NODE_ENV !== "development" || !state) {
    return null;
  }

  return (
    <div className="rounded-lg border border-dashed border-amber-600/40 bg-amber-50/80 px-3 py-2 font-mono text-[11px] leading-relaxed text-amber-950 dark:bg-amber-950/30 dark:text-amber-100">
      <p className="font-semibold">Placement debug</p>
      <p>image: {state.imageWidth}×{state.imageHeight}px</p>
      <p>stage: {state.stageWidth}×{state.stageHeight}px</p>
      {state.tapX != null && state.tapY != null ? (
        <p>
          tap: {state.tapX.toFixed(1)}, {state.tapY.toFixed(1)} →{" "}
          {state.xPercent?.toFixed(2)}%, {state.yPercent?.toFixed(2)}%
        </p>
      ) : (
        <p>tap: (none yet)</p>
      )}
      {state.suggestionKey ? <p>suggestion: {state.suggestionKey}</p> : null}
    </div>
  );
}
