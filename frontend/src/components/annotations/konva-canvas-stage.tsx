"use client";

import { Circle, Group, Image as KonvaImage, Layer, Rect, Stage, Text } from "react-konva";

import type { AnnotationCategory } from "@/lib/types";

export const PIN_RADIUS = 14;
export const HIT_RADIUS = 22;

export const CATEGORY_COLORS: Record<AnnotationCategory, string> = {
  observation: "#5c4d3c",
  symbol: "#7a5c2e",
  history: "#4a5d4a",
  question: "#5a4a6a",
  composition: "#3d4a5c",
  material: "#6b5a4a",
};

export interface PinView {
  id: number;
  x: number;
  y: number;
  color: string;
  label: string;
  category: AnnotationCategory;
  text: string;
}

type StagePointerEvent = {
  target: {
    getStage: () => {
      getPointerPosition: () => { x: number; y: number } | null;
    } | null;
  };
};

interface KonvaCanvasStageProps {
  width: number;
  height: number;
  image: HTMLImageElement | null;
  pins: PinView[];
  pendingPin: { x_percent: number; y_percent: number } | null;
  onStagePointer: (event: StagePointerEvent) => void;
}

export default function KonvaCanvasStage({
  width,
  height,
  image,
  pins,
  pendingPin,
  onStagePointer,
}: KonvaCanvasStageProps) {
  return (
    <Stage
      width={width}
      height={height}
      onClick={onStagePointer}
      onTap={onStagePointer}
    >
      <Layer>
        {image ? (
          <KonvaImage image={image} width={width} height={height} listening />
        ) : (
          <Rect width={width} height={height} fill="#f3efe8" listening />
        )}
        {pins.map((pin) => (
          <PinMarker key={pin.id} pin={pin} />
        ))}
        {pendingPin ? (
          <Circle
            x={(pendingPin.x_percent / 100) * width}
            y={(pendingPin.y_percent / 100) * height}
            radius={PIN_RADIUS}
            fill="#1f1a17"
            stroke="#faf7f2"
            strokeWidth={3}
            listening={false}
          />
        ) : null}
      </Layer>
    </Stage>
  );
}

function PinMarker({ pin }: { pin: PinView }) {
  return (
    <Group x={pin.x} y={pin.y} listening={false}>
      <Circle radius={HIT_RADIUS} fill="rgba(0,0,0,0.001)" listening={false} />
      <Circle
        radius={PIN_RADIUS}
        fill={pin.color}
        stroke="#faf7f2"
        strokeWidth={3}
        listening={false}
      />
      <Text
        x={PIN_RADIUS + 6}
        y={-8}
        text={pin.label}
        fontSize={14}
        fontStyle="600"
        fill={pin.color}
        listening={false}
      />
    </Group>
  );
}
