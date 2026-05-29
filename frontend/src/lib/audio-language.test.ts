import { describe, expect, it } from "vitest";

import {
  detect_transcript_language,
  map_whisper_language,
  refine_detected_language,
} from "@/lib/audio-language";

describe("audio-language", () => {
  it("detects English", () => {
    expect(detect_transcript_language("I notice the red clothing.")).toBe("en");
  });

  it("detects Farsi", () => {
    expect(detect_transcript_language("لباس قرمز و چهره رسمی کودک را می‌بینم.")).toBe("fa");
  });

  it("detects mixed English and Farsi", () => {
    expect(
      detect_transcript_language("I notice the red لباس and formal pose.")
    ).toBe("mixed");
  });

  it("maps whisper Persian codes", () => {
    expect(map_whisper_language("persian")).toBe("fa");
    expect(map_whisper_language("english")).toBe("en");
  });

  it("refines conflicting whisper and script hints to mixed", () => {
    expect(
      refine_detected_language("I notice the red clothing.", "persian")
    ).toBe("mixed");
  });
});
