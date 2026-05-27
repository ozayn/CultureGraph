export interface PlacementDebugState {
  imageWidth: number;
  imageHeight: number;
  stageWidth: number;
  stageHeight: number;
  tapX: number | null;
  tapY: number | null;
  xPercent: number | null;
  yPercent: number | null;
  suggestionKey: string | null;
}

export function emptyPlacementDebug(
  overrides: Partial<PlacementDebugState> = {}
): PlacementDebugState {
  return {
    imageWidth: 0,
    imageHeight: 0,
    stageWidth: 0,
    stageHeight: 0,
    tapX: null,
    tapY: null,
    xPercent: null,
    yPercent: null,
    suggestionKey: null,
    ...overrides,
  };
}
