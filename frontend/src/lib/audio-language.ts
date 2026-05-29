export type AudioNoteLanguage = "en" | "fa" | "mixed" | "unknown";

const PERSIAN_ARABIC_RE =
  /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/;
const LATIN_RE = /[A-Za-z]/;

export function mapWhisperLanguage(code: string | null | undefined): AudioNoteLanguage {
  if (!code) return "unknown";
  const normalized = code.trim().toLowerCase();
  if (normalized === "en" || normalized === "english") return "en";
  if (normalized === "fa" || normalized === "fas" || normalized === "persian" || normalized === "farsi") {
    return "fa";
  }
  return "unknown";
}

export function detectTranscriptLanguage(text: string): AudioNoteLanguage {
  const stripped = text.trim();
  if (!stripped) return "unknown";

  const hasPersian = PERSIAN_ARABIC_RE.test(stripped);
  const hasLatin = LATIN_RE.test(stripped);
  if (hasPersian && hasLatin) return "mixed";
  if (hasPersian) return "fa";
  if (hasLatin) return "en";
  return "unknown";
}

export function refineDetectedLanguage(
  text: string,
  whisperLanguage?: string | null
): AudioNoteLanguage {
  const heuristic = detectTranscriptLanguage(text);
  const whisper = mapWhisperLanguage(whisperLanguage);

  if (heuristic === "mixed") return "mixed";
  if (heuristic !== "unknown" && whisper !== "unknown" && heuristic !== whisper) {
    return "mixed";
  }
  if (heuristic !== "unknown") return heuristic;
  if (whisper !== "unknown") return whisper;
  return "unknown";
}

export function languageLabel(code: AudioNoteLanguage | null | undefined): string {
  switch (code) {
    case "en":
      return "English";
    case "fa":
      return "Farsi / Persian";
    case "mixed":
      return "English + Farsi";
    default:
      return "Unknown";
  }
}

// Test-friendly camelCase aliases matching backend naming in specs.
export const detect_transcript_language = detectTranscriptLanguage;
export const map_whisper_language = mapWhisperLanguage;
export const refine_detected_language = refineDetectedLanguage;
