import { ARTWORK_UPLOAD_MAX_BYTES, validateArtworkUploadFile } from "@/lib/upload-validation";
import { extractPhotoCaptureDate } from "@/lib/extract-photo-capture-date";

/** Long edge for client-side normalization before upload. */
export const UPLOAD_PREPARE_MAX_EDGE = 2000;
const PASS_THROUGH_MAX_EDGE = 2000;
const PASS_THROUGH_MAX_BYTES = 4 * 1024 * 1024;
const JPEG_QUALITY = 0.88;

export interface PrepareUploadResult {
  file: File;
  wasNormalized: boolean;
  originalSize: number;
  outputSize: number;
  capturedAt: string | null;
}

function loadImageElement(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Could not read image."));
    };
    image.src = url;
  });
}

function canvasToBlob(
  canvas: HTMLCanvasElement,
  type: string,
  quality?: number
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error("Could not prepare image."));
          return;
        }
        resolve(blob);
      },
      type,
      quality
    );
  });
}

function scaledDimensions(
  width: number,
  height: number,
  maxEdge: number
): { width: number; height: number } {
  const longest = Math.max(width, height);
  if (longest <= maxEdge) {
    return { width, height };
  }
  const scale = maxEdge / longest;
  return {
    width: Math.max(1, Math.round(width * scale)),
    height: Math.max(1, Math.round(height * scale)),
  };
}

function outputTypeFor(file: File): { mime: string; extension: string } {
  if (file.type === "image/png") {
    return { mime: "image/png", extension: "png" };
  }
  if (file.type === "image/webp") {
    return { mime: "image/webp", extension: "webp" };
  }
  return { mime: "image/jpeg", extension: "jpg" };
}

function buildFileName(originalName: string, extension: string): string {
  const base = originalName.replace(/\.[^.]+$/, "") || "photo";
  return `${base}.${extension}`;
}

/**
 * Resize/compress large photos for mobile upload. Skips re-encoding when already
 * small enough so EXIF and quality are preserved when possible.
 */
export async function prepareArtworkUploadFile(file: File): Promise<PrepareUploadResult> {
  const validationError = validateArtworkUploadFile(file);
  if (validationError) {
    throw new Error(validationError);
  }

  const capturedAt = await extractPhotoCaptureDate(file);
  const image = await loadImageElement(file);
  const { width, height } = scaledDimensions(
    image.naturalWidth,
    image.naturalHeight,
    UPLOAD_PREPARE_MAX_EDGE
  );

  const needsResize =
    width !== image.naturalWidth ||
    height !== image.naturalHeight ||
    file.size > PASS_THROUGH_MAX_BYTES;

  if (
    !needsResize &&
    image.naturalWidth <= PASS_THROUGH_MAX_EDGE &&
    image.naturalHeight <= PASS_THROUGH_MAX_EDGE
  ) {
    return {
      file,
      wasNormalized: false,
      originalSize: file.size,
      outputSize: file.size,
      capturedAt,
    };
  }

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) {
    throw new Error("Could not prepare image.");
  }
  context.drawImage(image, 0, 0, width, height);

  const { mime, extension } = outputTypeFor(file);
  let blob = await canvasToBlob(
    canvas,
    mime,
    mime === "image/jpeg" ? JPEG_QUALITY : undefined
  );

  if (blob.size > ARTWORK_UPLOAD_MAX_BYTES && mime !== "image/jpeg") {
    blob = await canvasToBlob(canvas, "image/jpeg", JPEG_QUALITY);
  }

  if (blob.size > ARTWORK_UPLOAD_MAX_BYTES) {
    let quality = JPEG_QUALITY;
    while (blob.size > ARTWORK_UPLOAD_MAX_BYTES && quality > 0.5) {
      quality -= 0.08;
      blob = await canvasToBlob(canvas, "image/jpeg", quality);
    }
  }

  if (blob.size > ARTWORK_UPLOAD_MAX_BYTES) {
    throw new Error("Image too large.");
  }

  const outputType = blob.type || "image/jpeg";
  const outputExtension = outputType.includes("png")
    ? "png"
    : outputType.includes("webp")
      ? "webp"
      : "jpg";

  const prepared = new File([blob], buildFileName(file.name, outputExtension), {
    type: outputType,
    lastModified: file.lastModified,
  });

  return {
    file: prepared,
    wasNormalized: true,
    originalSize: file.size,
    outputSize: prepared.size,
    capturedAt,
  };
}
