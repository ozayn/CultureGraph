"use client";

import { Circle, Group, Image as KonvaImage, Layer, Stage, Text } from "react-konva";

import type { AnnotationCategory } from "@/lib/types";

export const PIN_RADIUS = 14;
export const HIT_RADIUS = 22;

export const CATEGORY_COLORS: Record<AnnotationCategory, string> = {
  observation: "#5c4d3c",
  symbol: "#7a5c2e",
  history: "#4a5d4a",
  question: "#5a4a6a",
  composition: "#3d4a5c",
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

interface KonvaCanvasStageProps {
  width: number;
  height: number;
  image: HTMLImageElement | null;
  pins: PinView[];
  pendingPin: { x_percent: number; y_percent: number } | null;
  onStageTap: (event: {
    target: {
      getStage: () => {
        getPointerPosition: () => { x: number; y: number } | null;
      } | null;
    };
  }) => void;
}

export default function KonvaCanvasStage({
  width,
  height,
  image,
  pins,
  pendingPin,
  onStageTap,
}: KonvaCanvasStageProps) {
  return (
    <Stage width={width} height={height} onTap={onStageTap}>
      <Layer>
        {image ? (
          <KonvaImage image={image} width={width} height={height} />
        ) : null}
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
          />
        ) : null}
      </Layer>
    </Stage>
  );
}

function PinMarker({ pin }: { pin: PinView }) {
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
