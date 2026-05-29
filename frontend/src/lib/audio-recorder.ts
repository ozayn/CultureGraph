export const AUDIO_NOTE_MAX_DURATION_SECONDS = 300;

const PREFERRED_MIME_TYPES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4",
  "audio/ogg",
] as const;

export type AudioRecorderPhase = "idle" | "recording" | "recorded" | "error";

export interface AudioRecorderState {
  phase: AudioRecorderPhase;
  blob: Blob | null;
  durationSeconds: number;
  mimeType: string;
  error: string | null;
}

function pickMimeType(): string {
  if (typeof MediaRecorder === "undefined") {
    return "audio/webm";
  }
  for (const mimeType of PREFERRED_MIME_TYPES) {
    if (MediaRecorder.isTypeSupported(mimeType)) {
      return mimeType;
    }
  }
  return "audio/webm";
}

function extensionForMimeType(mimeType: string): string {
  if (mimeType.includes("mp4")) return ".m4a";
  if (mimeType.includes("wav")) return ".wav";
  if (mimeType.includes("ogg")) return ".ogg";
  return ".webm";
}

export function formatRecordingTimer(totalSeconds: number): string {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `${minutes}:${remainder.toString().padStart(2, "0")}`;
}

export function mapMicrophoneError(error: unknown): string {
  if (error instanceof DOMException) {
    if (error.name === "NotAllowedError" || error.name === "PermissionDeniedError") {
      return "Microphone access is blocked. Allow the mic in your browser settings and try again.";
    }
    if (error.name === "NotFoundError") {
      return "No microphone was found on this device.";
    }
    if (error.name === "NotReadableError") {
      return "The microphone is in use by another app.";
    }
  }
  return error instanceof Error ? error.message : "Could not access the microphone.";
}

export function blobToUploadFile(blob: Blob, mimeType: string): File {
  const extension = extensionForMimeType(mimeType);
  return new File([blob], `voice-note${extension}`, { type: mimeType || blob.type });
}

export class GalleryAudioRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private stream: MediaStream | null = null;
  private chunks: BlobPart[] = [];
  private startedAt = 0;
  private timerId: ReturnType<typeof setInterval> | null = null;
  private mimeType = pickMimeType();
  private onTick: ((seconds: number) => void) | null = null;
  private onAutoStop: (() => void) | null = null;

  getMimeType(): string {
    return this.mimeType;
  }

  async start(onTick?: (seconds: number) => void, onAutoStop?: () => void): Promise<void> {
    if (typeof window === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      throw new Error("Voice recording is not supported in this browser.");
    }

    this.onTick = onTick ?? null;
    this.onAutoStop = onAutoStop ?? null;
    this.chunks = [];

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (error) {
      throw new Error(mapMicrophoneError(error));
    }

    this.mediaRecorder = new MediaRecorder(this.stream, { mimeType: this.mimeType });
    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        this.chunks.push(event.data);
      }
    };

    this.startedAt = Date.now();
    this.mediaRecorder.start(250);
    this.timerId = setInterval(() => {
      const elapsed = (Date.now() - this.startedAt) / 1000;
      this.onTick?.(elapsed);
      if (elapsed >= AUDIO_NOTE_MAX_DURATION_SECONDS) {
        void this.stop();
        this.onAutoStop?.();
      }
    }, 200);
  }

  async stop(): Promise<{ blob: Blob; durationSeconds: number; mimeType: string }> {
    if (!this.mediaRecorder) {
      throw new Error("Recording has not started.");
    }

    if (this.timerId) {
      clearInterval(this.timerId);
      this.timerId = null;
    }

    const recorder = this.mediaRecorder;
    const durationSeconds = Math.min(
      AUDIO_NOTE_MAX_DURATION_SECONDS,
      Math.max(1, (Date.now() - this.startedAt) / 1000)
    );

    const blob = await new Promise<Blob>((resolve, reject) => {
      recorder.onstop = () => {
        resolve(new Blob(this.chunks, { type: this.mimeType }));
      };
      recorder.onerror = () => {
        reject(new Error("Recording failed."));
      };
      if (recorder.state !== "inactive") {
        recorder.stop();
      } else {
        resolve(new Blob(this.chunks, { type: this.mimeType }));
      }
    });

    this.cleanup();
    return { blob, durationSeconds, mimeType: this.mimeType };
  }

  discard(): void {
    this.cleanup();
  }

  private cleanup(): void {
    if (this.timerId) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
    if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
      this.mediaRecorder.stop();
    }
    this.mediaRecorder = null;
    if (this.stream) {
      for (const track of this.stream.getTracks()) {
        track.stop();
      }
      this.stream = null;
    }
    this.chunks = [];
    this.onTick = null;
    this.onAutoStop = null;
  }
}
