"use client";

import { Camera, ImagePlus } from "lucide-react";
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
  disabled?: boolean;
  className?: string;
  previewUrl?: string | null;
  selectedFile?: File | null;
  error?: string | null;
}

export function CameraUpload({
  onSelect,
  disabled,
  className,
  previewUrl,
  selectedFile,
  error,
}: CameraUploadProps) {
  const cameraRef = useRef<HTMLInputElement>(null);
  const libraryRef = useRef<HTMLInputElement>(null);

  function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) onSelect(file);
    event.target.value = "";
  }

  return (
    <div className={cn("space-y-3", className)}>
      <p className="text-sm text-muted-foreground">{ARTWORK_UPLOAD_GUIDANCE}</p>

      {previewUrl ? (
        <div className="overflow-hidden rounded-xl border border-border bg-muted/30">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={previewUrl}
            alt="Selected artwork"
            className="max-h-56 w-full object-contain"
          />
        </div>
      ) : null}

      {selectedFile ? (
        <p className="text-xs text-muted-foreground">
          Selected: {selectedFile.name} ({formatUploadFileSize(selectedFile.size)})
        </p>
      ) : null}

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <Button
          type="button"
          variant="outline"
          size="touch"
          className="w-full justify-start gap-3"
          disabled={disabled}
          onClick={() => cameraRef.current?.click()}
        >
          <Camera className="size-5" />
          Take photo
        </Button>
        <Button
          type="button"
          variant="outline"
          size="touch"
          className="w-full justify-start gap-3"
          disabled={disabled}
          onClick={() => libraryRef.current?.click()}
        >
          <ImagePlus className="size-5" />
          Choose photo
        </Button>
      </div>

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
