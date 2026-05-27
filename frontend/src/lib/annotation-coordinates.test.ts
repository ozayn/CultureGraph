import { describe, expect, it } from "vitest";

import {
  clampPercent,
  displayedImageRect,
  percentFromClientPoint,
  percentFromStagePoint,
  roundPercent,
} from "@/lib/annotation-coordinates";

describe("annotation-coordinates", () => {
  it("clamps and rounds percentages", () => {
    expect(clampPercent(120)).toBe(100);
    expect(clampPercent(-5)).toBe(0);
    expect(roundPercent(33.3333)).toBe(33.33);
  });

  it("converts stage pixels to percentages", () => {
    const result = percentFromStagePoint({ x: 160, y: 90 }, { width: 320, height: 180 });
    expect(result).toEqual({ x_percent: 50, y_percent: 50 });
  });

  it("returns null for invalid stage size", () => {
    expect(percentFromStagePoint({ x: 10, y: 10 }, { width: 0, height: 100 })).toBeNull();
  });

  it("computes letterboxed image rect for object-fit contain", () => {
    const rect = displayedImageRect(
      { width: 400, height: 300 },
      { width: 800, height: 800 }
    );
    expect(rect).not.toBeNull();
    expect(rect?.width).toBe(300);
    expect(rect?.height).toBe(300);
    expect(rect?.x).toBe(50);
    expect(rect?.y).toBe(0);
  });

  it("maps client coordinates through displayed image rect", () => {
    const container = {
      left: 100,
      top: 50,
      width: 400,
      height: 300,
    } as DOMRectReadOnly;
    const imageRect = displayedImageRect(
      { width: container.width, height: container.height },
      { width: 800, height: 800 }
    );
    expect(imageRect).not.toBeNull();

    const centerX = container.left + (imageRect?.x ?? 0) + (imageRect?.width ?? 0) / 2;
    const centerY = container.top + (imageRect?.y ?? 0) + (imageRect?.height ?? 0) / 2;

    const result = percentFromClientPoint(centerX, centerY, container, imageRect!);
    expect(result?.x_percent).toBe(50);
    expect(result?.y_percent).toBe(50);
  });

  it("rejects taps outside the displayed image area", () => {
    const container = {
      left: 0,
      top: 0,
      width: 400,
      height: 300,
    } as DOMRectReadOnly;
    const imageRect = displayedImageRect(
      { width: container.width, height: container.height },
      { width: 1600, height: 400 }
    );
    expect(imageRect).not.toBeNull();
    expect(percentFromClientPoint(10, 10, container, imageRect!)).toBeNull();
  });
});
