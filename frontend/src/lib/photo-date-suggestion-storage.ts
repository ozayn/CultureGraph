const DISMISS_PREFIX = "culturegraph:photo-date-dismissed:";

export function photoDateDismissKey(artworkId: number): string {
  return `${DISMISS_PREFIX}${artworkId}`;
}

export function isPhotoDateSuggestionDismissed(artworkId: number): boolean {
  if (typeof window === "undefined") return false;
  return window.sessionStorage.getItem(photoDateDismissKey(artworkId)) === "1";
}

export function dismissPhotoDateSuggestion(artworkId: number): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(photoDateDismissKey(artworkId), "1");
}
