export interface Size {
  width: number;
  height: number;
}

export interface Point {
  x: number;
  y: number;
}

export interface PercentPoint {
  x_percent: number;
  y_percent: number;
}

export interface DisplayedImageRect extends Point, Size {}

/** Clamp a percentage coordinate to the valid pin range. */
export function clampPercent(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.min(100, Math.max(0, value));
}

/** Round to two decimal places for stable API payloads. */
export function roundPercent(value: number): number {
  return Number(clampPercent(value).toFixed(2));
}

/**
 * Convert a pointer position in stage/canvas pixel space to image percentages.
 * Stage dimensions must match the displayed image area (same aspect ratio).
 */
export function percentFromStagePoint(
  point: Point,
  stageSize: Size
): PercentPoint | null {
  if (stageSize.width <= 0 || stageSize.height <= 0) {
    return null;
  }

  return {
    x_percent: roundPercent((point.x / stageSize.width) * 100),
    y_percent: roundPercent((point.y / stageSize.height) * 100),
  };
}

/**
 * object-fit: contain — compute the letterboxed image rect inside a container.
 */
export function displayedImageRect(
  container: Size,
  imageNatural: Size
): DisplayedImageRect | null {
  if (
    container.width <= 0 ||
    container.height <= 0 ||
    imageNatural.width <= 0 ||
    imageNatural.height <= 0
  ) {
    return null;
  }

  const containerAspect = container.width / container.height;
  const imageAspect = imageNatural.width / imageNatural.height;

  let width = container.width;
  let height = container.height;
  let x = 0;
  let y = 0;

  if (imageAspect > containerAspect) {
    height = container.width / imageAspect;
    y = (container.height - height) / 2;
  } else {
    width = container.height * imageAspect;
    x = (container.width - width) / 2;
  }

  return { x, y, width, height };
}

/**
 * Map a viewport/client pointer to percentages using the displayed image rect.
 */
export function percentFromClientPoint(
  clientX: number,
  clientY: number,
  containerRect: DOMRectReadOnly,
  imageRect: DisplayedImageRect
): PercentPoint | null {
  const localX = clientX - containerRect.left - imageRect.x;
  const localY = clientY - containerRect.top - imageRect.y;

  if (
    localX < 0 ||
    localY < 0 ||
    localX > imageRect.width ||
    localY > imageRect.height
  ) {
    return null;
  }

  return {
    x_percent: roundPercent((localX / imageRect.width) * 100),
    y_percent: roundPercent((localY / imageRect.height) * 100),
  };
}
