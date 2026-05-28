import { describe, expect, it, beforeEach } from "vitest";

import {
  dismissPhotoDateSuggestion,
  isPhotoDateSuggestionDismissed,
  photoDateDismissKey,
} from "@/lib/photo-date-suggestion-storage";

describe("photo-date-suggestion-storage", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it("tracks dismiss state per artwork", () => {
    expect(isPhotoDateSuggestionDismissed(7)).toBe(false);
    dismissPhotoDateSuggestion(7);
    expect(window.sessionStorage.getItem(photoDateDismissKey(7))).toBe("1");
    expect(isPhotoDateSuggestionDismissed(7)).toBe(true);
    expect(isPhotoDateSuggestionDismissed(8)).toBe(false);
  });
});
