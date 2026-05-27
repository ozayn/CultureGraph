"use client";

import { Camera, ImagePlus, Trash2 } from "lucide-react";
import { useRef } from "react";

import { Button } from "@/components/ui/button";
import {
  ARTWORK_UPLOAD_ACCEPT,
  ARTWORK_UPLOAD_GUIDANCE,
  formatUploadFileSize,
} from "@/lib/upload-validation";
import { cn } from "@/lib/utils";

interface CameraUploadProps {
  onSelect: (file: File) => void;
  onRemove?: () => void;
  disabled?: boolean;
  className?: string;
  previewUrl?: string | null;
  selectedFile?: File | null;
  error?: string | null;
  variant?: "default" | "compact";
}

export function CameraUpload({
  onSelect,
  onRemove,
  disabled,
  className,
  previewUrl,
  selectedFile,
  error,
  variant = "default",
}: CameraUploadProps) {
  const cameraRef = useRef<HTMLInputElement>(null);
  const libraryRef = useRef<HTMLInputElement>(null);
  const compact = variant === "compact";

  function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) onSelect(file);
    event.target.value = "";
  }

  return (
    <div className={cn(compact ? "space-y-2" : "space-y-3", className)}>
      {!compact ? (
        <p className="text-sm text-muted-foreground">{ARTWORK_UPLOAD_GUIDANCE}</p>
      ) : null}

      {previewUrl ? (
        <div
          className={cn(
            "flex items-center gap-3 rounded-xl border border-border bg-muted/30 p-2",
            compact ? "max-h-36" : "max-h-56"
          )}
        >
          <div className="relative size-24 shrink-0 overflow-hidden rounded-lg bg-muted sm:size-28">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={previewUrl}
              alt="Selected artwork"
              className="size-full object-cover"
            />
          </div>
          <div className="min-w-0 flex-1 space-y-2">
            {selectedFile ? (
              <p className="truncate text-xs text-muted-foreground">
                {selectedFile.name} · {formatUploadFileSize(selectedFile.size)}
              </p>
            ) : null}
            {onRemove ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="min-h-9"
                disabled={disabled}
                onClick={onRemove}
              >
                <Trash2 className="size-4" />
                Remove photo
              </Button>
            ) : null}
          </div>
        </div>
      ) : null}

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <div className={cn("grid gap-2", compact ? "grid-cols-2" : "grid-cols-1 sm:grid-cols-2")}>
        <Button
          type="button"
          variant="outline"
          size="touch"
          className={cn("w-full justify-start gap-2", compact && "min-h-11 px-3")}
          disabled={disabled}
          onClick={() => cameraRef.current?.click()}
        >
          <Camera className="size-5 shrink-0" />
          <span className="truncate">Take photo</span>
        </Button>
        <Button
          type="button"
          variant="outline"
          size="touch"
          className={cn("w-full justify-start gap-2", compact && "min-h-11 px-3")}
          disabled={disabled}
          onClick={() => libraryRef.current?.click()}
        >
          <ImagePlus className="size-5 shrink-0" />
          <span className="truncate">Choose photo</span>
        </Button>
      </div>

      {compact ? (
        <p className="text-[11px] leading-snug text-muted-foreground">{ARTWORK_UPLOAD_GUIDANCE}</p>
      ) : null}

      <input
        ref={cameraRef}
        type="file"
        accept={ARTWORK_UPLOAD_ACCEPT}
        capture="environment"
        className="hidden"
        onChange={handleChange}
      />
      <input
        ref={libraryRef}
        type="file"
        accept={ARTWORK_UPLOAD_ACCEPT}
        className="hidden"
        onChange={handleChange}
      />
    </div>
  );
}
