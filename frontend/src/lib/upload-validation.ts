export const ARTWORK_UPLOAD_MAX_BYTES = 10 * 1024 * 1024;
export const ARTWORK_UPLOAD_ACCEPT = "image/jpeg,image/png,image/webp";
export const ARTWORK_UPLOAD_GUIDANCE = "JPEG, PNG, or WebP up to 10 MB.";

const ACCEPTED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

export function validateArtworkUploadFile(file: File): string | null {
  if (!ACCEPTED_TYPES.has(file.type)) {
    return "Upload a JPEG, PNG, or WebP image.";
  }

  if (file.size > ARTWORK_UPLOAD_MAX_BYTES) {
    return "Photo must be 10 MB or smaller.";
  }

  return null;
}

export function formatUploadFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
